"""Physically dimensioned spectroscopy and aerosol attenuation helpers.

The functions in this module consume the processed HITRAN table produced by
``scripts/download_external_data.py``. Molecular cross sections are evaluated
in wavenumber space with temperature adjusted HITRAN intensities, TIPS
partition sums from HAPI, pressure broadening, pressure shift, Doppler
broadening, and a normalized Voigt profile from :func:`scipy.special.wofz`.

The layered integration is deliberately a vertical, plane parallel reference
calculation. A separate airmass factor converts zenith attenuation to a slant
path. Pollutant scale heights are modeling assumptions rather than measured
vertical profiles and are therefore explicit arguments.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from hapi import partitionSum
from scipy.constants import Avogadro, Boltzmann, speed_of_light
from scipy.special import wofz


GHZ_PER_WAVENUMBER = 29.9792458
REFERENCE_TEMPERATURE_K = 296.0
REFERENCE_PRESSURE_PA = 101_325.0
SECOND_RADIATION_CONSTANT_CM_K = 1.438_776_877
DB_PER_NEPER = 10.0 / np.log(10.0)
DRY_AIR_O2_MOLE_FRACTION = 0.20946

TARGET_GASES = ("CO", "O3", "SO2", "NO2")
BACKGROUND_GASES = ("H2O", "O2")

# Main isotopologue molar masses. The processed project table currently uses
# isotopologue 1 for every molecule.
MOLAR_MASS_G_MOL = {
    "H2O": 18.010565,
    "CO": 27.994915,
    "O2": 31.989830,
    "O3": 47.984745,
    "NO2": 45.992904,
    "SO2": 63.961901,
}

REQUIRED_HITRAN_COLUMNS = {
    "molecule",
    "molecule_id",
    "isotopologue_id",
    "wavenumber_cm_1",
    "line_intensity",
    "gamma_air",
    "lower_state_energy",
    "temperature_exponent",
    "air_pressure_shift",
}


@dataclass(frozen=True)
class AtmosphereProfile:
    """Layer midpoint properties for a standard lower atmosphere."""

    altitude_m: np.ndarray
    layer_thickness_m: np.ndarray
    temperature_k: np.ndarray
    pressure_pa: np.ndarray


@dataclass(frozen=True)
class PMMode:
    """Monodisperse Rayleigh particle assumptions for one PM mode."""

    diameter_um: float
    density_kg_m3: float
    refractive_index: complex


DEFAULT_FINE_PM_MODE = PMMode(
    diameter_um=1.0,
    density_kg_m3=1_500.0,
    refractive_index=1.50 + 0.01j,
)
DEFAULT_COARSE_PM_MODE = PMMode(
    diameter_um=6.0,
    density_kg_m3=1_800.0,
    refractive_index=1.53 + 0.01j,
)


@dataclass(frozen=True)
class ZenithAttenuationDesign:
    """Vertically integrated attenuation components at zenith.

    ``gas_db_per_ug_m3`` has one column per entry in ``gas_names``.
    ``pm_db_per_ug_m3`` has a fine PM2.5 column and a coarse
    ``PM10 - PM2.5`` column. This representation prevents PM2.5 mass from
    being counted a second time as part of PM10.
    """

    frequency_ghz: np.ndarray
    gas_names: tuple[str, ...]
    gas_db_per_ug_m3: np.ndarray
    background_db: np.ndarray
    pm_names: tuple[str, str]
    pm_db_per_ug_m3: np.ndarray
    atmosphere: AtmosphereProfile

    def attenuation_db(
        self,
        gas_surface_ug_m3: Mapping[str, float] | None = None,
        *,
        pm25_ug_m3: float = 0.0,
        pm10_ug_m3: float = 0.0,
        elevation_deg: float = 90.0,
        include_background: bool = True,
    ) -> np.ndarray:
        """Combine design columns for one surface concentration scenario.

        Gas mappings may use symbols such as ``"CO"`` or processed column
        names such as ``"CO_ug_m3"``. PM10 is treated as total mass below
        10 micrometers, so only ``max(PM10 - PM2.5, 0)`` enters the coarse
        mode.
        """

        concentrations = gas_surface_ug_m3 or {}
        gas_values = []
        for gas in self.gas_names:
            value = concentrations.get(gas, concentrations.get(f"{gas}_ug_m3", 0.0))
            gas_values.append(_nonnegative_scalar(value, f"{gas} concentration"))

        pm25 = _nonnegative_scalar(pm25_ug_m3, "PM2.5 concentration")
        pm10 = _nonnegative_scalar(pm10_ug_m3, "PM10 concentration")
        coarse_pm = max(pm10 - pm25, 0.0)

        zenith = self.gas_db_per_ug_m3 @ np.asarray(gas_values, dtype=float)
        zenith = zenith + self.pm_db_per_ug_m3 @ np.asarray([pm25, coarse_pm])
        if include_background:
            zenith = zenith + self.background_db
        return apply_plane_parallel_slant(zenith, elevation_deg)


def concentration_ug_m3_to_number_density_cm3(
    concentration_ug_m3: np.ndarray | float,
    molar_mass_g_mol: float,
) -> np.ndarray:
    """Convert mass concentration in micrograms per cubic meter to molecules per cubic centimeter."""

    concentration = np.asarray(concentration_ug_m3, dtype=float)
    if not np.isfinite(concentration).all() or np.any(concentration < 0.0):
        raise ValueError("Concentration must be finite and nonnegative.")
    if not np.isfinite(molar_mass_g_mol) or molar_mass_g_mol <= 0.0:
        raise ValueError("Molar mass must be finite and positive.")
    return concentration * Avogadro * 1.0e-12 / molar_mass_g_mol


def voigt_profile_wavenumber(
    wavenumber_cm_1: np.ndarray,
    center_cm_1: np.ndarray | float,
    gaussian_sigma_cm_1: np.ndarray | float,
    lorentz_hwhm_cm_1: np.ndarray | float,
) -> np.ndarray:
    """Return a normalized Voigt profile in inverse wavenumber units.

    Gaussian width is one standard deviation and the Lorentz width is the
    half width at half maximum. Integrating the returned profile over
    wavenumber gives unity when the numerical grid covers the tails.
    """

    grid = np.asarray(wavenumber_cm_1, dtype=float)
    center = np.asarray(center_cm_1, dtype=float)
    sigma = np.asarray(gaussian_sigma_cm_1, dtype=float)
    gamma = np.asarray(lorentz_hwhm_cm_1, dtype=float)
    if np.any(~np.isfinite(grid)) or np.any(~np.isfinite(center)):
        raise ValueError("Wavenumbers and line centers must be finite.")
    if np.any(~np.isfinite(sigma)) or np.any(sigma <= 0.0):
        raise ValueError("Gaussian sigma must be finite and positive.")
    if np.any(~np.isfinite(gamma)) or np.any(gamma < 0.0):
        raise ValueError("Lorentz width must be finite and nonnegative.")

    z = ((grid - center) + 1j * gamma) / (sigma * np.sqrt(2.0))
    profile = np.real(wofz(z)) / (sigma * np.sqrt(2.0 * np.pi))
    return np.maximum(profile, 0.0)


def molecular_cross_section_cm2_per_molecule(
    hitran_lines: pd.DataFrame,
    frequency_ghz: np.ndarray,
    molecule: str,
    *,
    temperature_k: float,
    pressure_pa: float,
    partition_sum_version: int = 2025,
    chunk_size: int = 256,
) -> np.ndarray:
    """Evaluate a molecule's Voigt cross section on a frequency grid.

    Air broadening is used for all species. Self broadening is omitted, which
    is appropriate for trace pollutants and is a first order approximation
    for the water background.
    """

    _validate_hitran_table(hitran_lines)
    frequency = _positive_frequency_grid(frequency_ghz)
    if molecule not in MOLAR_MASS_G_MOL:
        raise ValueError(f"No molar mass configured for molecule {molecule}.")
    if not np.isfinite(temperature_k) or temperature_k <= 0.0:
        raise ValueError("Temperature must be finite and positive.")
    if not np.isfinite(pressure_pa) or pressure_pa < 0.0:
        raise ValueError("Pressure must be finite and nonnegative.")
    if chunk_size < 1:
        raise ValueError("Chunk size must be positive.")

    selected = hitran_lines.loc[hitran_lines["molecule"] == molecule].copy()
    if selected.empty:
        raise ValueError(f"No HITRAN lines found for molecule {molecule}.")

    grid_cm_1 = frequency / GHZ_PER_WAVENUMBER
    cross_section = np.zeros_like(grid_cm_1)
    pressure_atm = pressure_pa / REFERENCE_PRESSURE_PA
    mass_kg_per_molecule = MOLAR_MASS_G_MOL[molecule] * 1.0e-3 / Avogadro

    grouped = selected.groupby(["molecule_id", "isotopologue_id"], sort=False)
    for (molecule_id, isotopologue_id), group in grouped:
        numeric = group[
            [
                "wavenumber_cm_1",
                "line_intensity",
                "gamma_air",
                "lower_state_energy",
                "temperature_exponent",
                "air_pressure_shift",
            ]
        ].apply(pd.to_numeric, errors="coerce")
        numeric = numeric.replace([np.inf, -np.inf], np.nan).dropna()
        numeric = numeric.loc[
            (numeric["wavenumber_cm_1"] > 0.0)
            & (numeric["line_intensity"] > 0.0)
            & (numeric["gamma_air"] >= 0.0)
        ]
        if numeric.empty:
            continue

        nu = numeric["wavenumber_cm_1"].to_numpy(dtype=float)
        intensity_ref = numeric["line_intensity"].to_numpy(dtype=float)
        lower_energy = numeric["lower_state_energy"].to_numpy(dtype=float)
        gamma_air = numeric["gamma_air"].to_numpy(dtype=float)
        temperature_exponent = numeric["temperature_exponent"].to_numpy(dtype=float)
        pressure_shift = numeric["air_pressure_shift"].to_numpy(dtype=float)

        q_ref = float(
            partitionSum(
                int(molecule_id),
                int(isotopologue_id),
                REFERENCE_TEMPERATURE_K,
                version=partition_sum_version,
            )
        )
        q_temperature = float(
            partitionSum(
                int(molecule_id),
                int(isotopologue_id),
                float(temperature_k),
                version=partition_sum_version,
            )
        )
        if q_ref <= 0.0 or q_temperature <= 0.0:
            raise ValueError("HAPI returned a nonpositive partition sum.")

        boltzmann_factor = np.exp(
            -SECOND_RADIATION_CONSTANT_CM_K
            * lower_energy
            * (1.0 / temperature_k - 1.0 / REFERENCE_TEMPERATURE_K)
        )
        stimulated_temperature = -np.expm1(
            -SECOND_RADIATION_CONSTANT_CM_K * nu / temperature_k
        )
        stimulated_reference = -np.expm1(
            -SECOND_RADIATION_CONSTANT_CM_K * nu / REFERENCE_TEMPERATURE_K
        )
        intensity_temperature = (
            intensity_ref
            * (q_ref / q_temperature)
            * boltzmann_factor
            * (stimulated_temperature / stimulated_reference)
        )

        shifted_center = nu + pressure_shift * pressure_atm
        lorentz_hwhm = (
            gamma_air
            * pressure_atm
            * (REFERENCE_TEMPERATURE_K / temperature_k) ** temperature_exponent
        )
        doppler_sigma = np.abs(shifted_center) * np.sqrt(
            Boltzmann * temperature_k / (mass_kg_per_molecule * speed_of_light**2)
        )
        doppler_sigma = np.maximum(doppler_sigma, np.finfo(float).tiny)

        for start in range(0, len(numeric), chunk_size):
            stop = min(start + chunk_size, len(numeric))
            profile = voigt_profile_wavenumber(
                grid_cm_1[None, :],
                shifted_center[start:stop, None],
                doppler_sigma[start:stop, None],
                lorentz_hwhm[start:stop, None],
            )
            cross_section += np.sum(intensity_temperature[start:stop, None] * profile, axis=0)

    if not np.isfinite(cross_section).all():
        raise FloatingPointError(f"Nonfinite cross section calculated for {molecule}.")
    return np.maximum(cross_section, 0.0)


def standard_troposphere_profile(
    *,
    n_layers: int = 24,
    top_altitude_m: float = 12_000.0,
    surface_temperature_k: float = 288.15,
    surface_pressure_pa: float = REFERENCE_PRESSURE_PA,
) -> AtmosphereProfile:
    """Create a US standard atmosphere style profile through the lower stratosphere."""

    if n_layers < 1:
        raise ValueError("At least one atmosphere layer is required.")
    if not np.isfinite(top_altitude_m) or not 0.0 < top_altitude_m <= 20_000.0:
        raise ValueError("Top altitude must be in the interval (0, 20000] meters.")
    surface_temperature = _positive_scalar(surface_temperature_k, "Surface temperature")
    surface_pressure = _positive_scalar(surface_pressure_pa, "Surface pressure")

    edges_m = np.linspace(0.0, top_altitude_m, n_layers + 1)
    altitude_m = 0.5 * (edges_m[:-1] + edges_m[1:])
    thickness_m = np.diff(edges_m)

    lapse_rate_k_m = 0.0065
    gravity_m_s2 = 9.80665
    dry_air_molar_mass_kg_mol = 0.0289644
    gas_constant_j_mol_k = 8.314462618
    tropopause_m = 11_000.0
    exponent = gravity_m_s2 * dry_air_molar_mass_kg_mol / (gas_constant_j_mol_k * lapse_rate_k_m)

    temperature_k = surface_temperature - lapse_rate_k_m * np.minimum(altitude_m, tropopause_m)
    if np.any(temperature_k <= 0.0):
        raise ValueError("Surface temperature and altitude produce a nonphysical profile.")
    pressure_pa = np.empty_like(altitude_m)
    below = altitude_m <= tropopause_m
    pressure_pa[below] = surface_pressure * (
        temperature_k[below] / surface_temperature
    ) ** exponent

    tropopause_temperature_k = surface_temperature - lapse_rate_k_m * tropopause_m
    if tropopause_temperature_k <= 0.0:
        raise ValueError("Surface temperature produces a nonphysical tropopause temperature.")
    tropopause_pressure_pa = surface_pressure * (
        tropopause_temperature_k / surface_temperature
    ) ** exponent
    pressure_pa[~below] = tropopause_pressure_pa * np.exp(
        -gravity_m_s2
        * dry_air_molar_mass_kg_mol
        * (altitude_m[~below] - tropopause_m)
        / (gas_constant_j_mol_k * tropopause_temperature_k)
    )

    return AtmosphereProfile(
        altitude_m=altitude_m,
        layer_thickness_m=thickness_m,
        temperature_k=temperature_k,
        pressure_pa=pressure_pa,
    )


def water_vapor_pressure_pa_from_dew_point(surface_dew_point_c: float) -> float:
    """Return surface water vapor pressure using the Buck dew point equations."""

    dew_point = float(surface_dew_point_c)
    if not np.isfinite(dew_point) or not -80.0 <= dew_point <= 60.0:
        raise ValueError("Surface dew point must be between -80 and 60 degrees Celsius.")
    if dew_point >= 0.0:
        vapor_hpa = 6.1121 * np.exp((18.678 - dew_point / 234.5) * dew_point / (257.14 + dew_point))
    else:
        vapor_hpa = 6.1115 * np.exp((23.036 - dew_point / 333.7) * dew_point / (279.82 + dew_point))
    return float(vapor_hpa * 100.0)


def rayleigh_mass_extinction_m2_per_kg(
    frequency_ghz: np.ndarray,
    *,
    particle_diameter_um: float,
    particle_density_kg_m3: float,
    refractive_index: complex,
) -> np.ndarray:
    """Return Rayleigh absorption plus scattering mass extinction.

    The complex polarizability factor is ``(m^2 - 1) / (m^2 + 2)``. The
    magnitude of its imaginary part is used so either common refractive index
    sign convention produces nonnegative absorption. The approximation is
    rejected when the maximum size parameter exceeds 0.3.
    """

    frequency = _positive_frequency_grid(frequency_ghz)
    diameter_m = float(particle_diameter_um) * 1.0e-6
    density = float(particle_density_kg_m3)
    index = complex(refractive_index)
    if not np.isfinite(diameter_m) or diameter_m <= 0.0:
        raise ValueError("Particle diameter must be finite and positive.")
    if not np.isfinite(density) or density <= 0.0:
        raise ValueError("Particle density must be finite and positive.")
    if not np.isfinite(index.real) or not np.isfinite(index.imag):
        raise ValueError("Refractive index must be finite.")

    radius_m = 0.5 * diameter_m
    wave_number_m_1 = 2.0 * np.pi * frequency * 1.0e9 / speed_of_light
    size_parameter = wave_number_m_1 * radius_m
    if np.max(size_parameter) > 0.3:
        raise ValueError("Particle size is outside the configured Rayleigh regime.")

    polarizability = (index**2 - 1.0) / (index**2 + 2.0)
    absorption_cross_section_m2 = (
        4.0 * np.pi * wave_number_m_1 * radius_m**3 * abs(polarizability.imag)
    )
    scattering_cross_section_m2 = (
        8.0
        * np.pi
        / 3.0
        * wave_number_m_1**4
        * radius_m**6
        * abs(polarizability) ** 2
    )
    particle_mass_kg = 4.0 * np.pi / 3.0 * radius_m**3 * density
    extinction = (absorption_cross_section_m2 + scattering_cross_section_m2) / particle_mass_kg
    return np.maximum(extinction, 0.0)


def build_layered_zenith_attenuation_design(
    hitran_lines: pd.DataFrame,
    frequency_ghz: np.ndarray,
    *,
    surface_dew_point_c: float = 10.0,
    pollutant_scale_height_m: float | Mapping[str, float] = 1_500.0,
    water_scale_height_m: float = 2_000.0,
    pm_scale_height_m: float = 1_000.0,
    n_layers: int = 24,
    top_altitude_m: float = 12_000.0,
    surface_temperature_k: float = 288.15,
    surface_pressure_pa: float = REFERENCE_PRESSURE_PA,
    fine_pm_mode: PMMode = DEFAULT_FINE_PM_MODE,
    coarse_pm_mode: PMMode = DEFAULT_COARSE_PM_MODE,
    partition_sum_version: int = 2025,
) -> ZenithAttenuationDesign:
    """Build vertical gas, background, and PM attenuation design columns."""

    _validate_hitran_table(hitran_lines)
    frequency = _positive_frequency_grid(frequency_ghz)
    atmosphere = standard_troposphere_profile(
        n_layers=n_layers,
        top_altitude_m=top_altitude_m,
        surface_temperature_k=surface_temperature_k,
        surface_pressure_pa=surface_pressure_pa,
    )
    water_scale = _positive_scalar(water_scale_height_m, "Water scale height")
    pm_scale = _positive_scalar(pm_scale_height_m, "PM scale height")
    pollutant_scales = {
        gas: _pollutant_scale_height(gas, pollutant_scale_height_m) for gas in TARGET_GASES
    }

    cross_sections: dict[str, np.ndarray] = {}
    for molecule in TARGET_GASES + BACKGROUND_GASES:
        cross_sections[molecule] = np.vstack(
            [
                molecular_cross_section_cm2_per_molecule(
                    hitran_lines,
                    frequency,
                    molecule,
                    temperature_k=float(temperature_k),
                    pressure_pa=float(pressure_pa),
                    partition_sum_version=partition_sum_version,
                )
                for temperature_k, pressure_pa in zip(
                    atmosphere.temperature_k,
                    atmosphere.pressure_pa,
                    strict=True,
                )
            ]
        )

    dz_cm = atmosphere.layer_thickness_m * 100.0
    gas_columns = []
    for gas in TARGET_GASES:
        surface_number_density_per_ug_m3 = float(
            concentration_ug_m3_to_number_density_cm3(1.0, MOLAR_MASS_G_MOL[gas])
        )
        number_density_cm3 = surface_number_density_per_ug_m3 * np.exp(
            -atmosphere.altitude_m / pollutant_scales[gas]
        )
        optical_depth_per_ug_m3 = np.sum(
            cross_sections[gas] * (number_density_cm3 * dz_cm)[:, None],
            axis=0,
        )
        gas_columns.append(DB_PER_NEPER * optical_depth_per_ug_m3)

    surface_water_pressure_pa = water_vapor_pressure_pa_from_dew_point(surface_dew_point_c)
    surface_water_number_density_cm3 = (
        surface_water_pressure_pa / (Boltzmann * float(surface_temperature_k)) / 1.0e6
    )
    water_number_density_cm3 = surface_water_number_density_cm3 * np.exp(
        -atmosphere.altitude_m / water_scale
    )
    total_air_number_density_cm3 = (
        atmosphere.pressure_pa / (Boltzmann * atmosphere.temperature_k) / 1.0e6
    )
    water_number_density_cm3 = np.minimum(water_number_density_cm3, 0.99 * total_air_number_density_cm3)
    dry_air_number_density_cm3 = np.maximum(
        total_air_number_density_cm3 - water_number_density_cm3,
        0.0,
    )
    oxygen_number_density_cm3 = DRY_AIR_O2_MOLE_FRACTION * dry_air_number_density_cm3
    background_optical_depth = np.sum(
        (
            cross_sections["H2O"] * water_number_density_cm3[:, None]
            + cross_sections["O2"] * oxygen_number_density_cm3[:, None]
        )
        * dz_cm[:, None],
        axis=0,
    )

    pm_vertical_mass_column_kg_m2_per_ug_m3 = 1.0e-9 * np.sum(
        np.exp(-atmosphere.altitude_m / pm_scale) * atmosphere.layer_thickness_m
    )
    fine_extinction = rayleigh_mass_extinction_m2_per_kg(
        frequency,
        particle_diameter_um=fine_pm_mode.diameter_um,
        particle_density_kg_m3=fine_pm_mode.density_kg_m3,
        refractive_index=fine_pm_mode.refractive_index,
    )
    coarse_extinction = rayleigh_mass_extinction_m2_per_kg(
        frequency,
        particle_diameter_um=coarse_pm_mode.diameter_um,
        particle_density_kg_m3=coarse_pm_mode.density_kg_m3,
        refractive_index=coarse_pm_mode.refractive_index,
    )
    pm_columns = DB_PER_NEPER * pm_vertical_mass_column_kg_m2_per_ug_m3 * np.column_stack(
        [fine_extinction, coarse_extinction]
    )

    return ZenithAttenuationDesign(
        frequency_ghz=frequency,
        gas_names=TARGET_GASES,
        gas_db_per_ug_m3=np.column_stack(gas_columns),
        background_db=DB_PER_NEPER * background_optical_depth,
        pm_names=("PM2_5_ug_m3", "PM10_minus_PM2_5_ug_m3"),
        pm_db_per_ug_m3=pm_columns,
        atmosphere=atmosphere,
    )


def plane_parallel_airmass(elevation_deg: np.ndarray | float) -> np.ndarray:
    """Return the plane parallel airmass factor for elevation angles."""

    elevation = np.asarray(elevation_deg, dtype=float)
    if not np.isfinite(elevation).all() or np.any((elevation <= 0.0) | (elevation > 90.0)):
        raise ValueError("Elevation must be in the interval (0, 90] degrees.")
    return 1.0 / np.sin(np.deg2rad(elevation))


def apply_plane_parallel_slant(
    zenith_attenuation_db: np.ndarray,
    elevation_deg: np.ndarray | float,
) -> np.ndarray:
    """Scale zenith attenuation to one or more plane parallel slant paths."""

    zenith = np.asarray(zenith_attenuation_db, dtype=float)
    if not np.isfinite(zenith).all() or np.any(zenith < 0.0):
        raise ValueError("Zenith attenuation must be finite and nonnegative.")
    factor = plane_parallel_airmass(elevation_deg)
    if factor.ndim == 0:
        return zenith * float(factor)
    return factor[..., None] * zenith


def _validate_hitran_table(hitran_lines: pd.DataFrame) -> None:
    if not isinstance(hitran_lines, pd.DataFrame):
        raise TypeError("HITRAN lines must be provided as a pandas DataFrame.")
    missing = REQUIRED_HITRAN_COLUMNS.difference(hitran_lines.columns)
    if missing:
        raise ValueError(f"Processed HITRAN table is missing columns: {sorted(missing)}")


def _positive_frequency_grid(frequency_ghz: np.ndarray) -> np.ndarray:
    frequency = np.asarray(frequency_ghz, dtype=float)
    if frequency.ndim != 1 or frequency.size == 0:
        raise ValueError("Frequency grid must be a nonempty one dimensional array.")
    if not np.isfinite(frequency).all() or np.any(frequency <= 0.0):
        raise ValueError("Frequencies must be finite and positive.")
    return frequency


def _positive_scalar(value: float, name: str) -> float:
    scalar = float(value)
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return scalar


def _nonnegative_scalar(value: float, name: str) -> float:
    scalar = float(value)
    if not np.isfinite(scalar) or scalar < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative.")
    return scalar


def _pollutant_scale_height(
    molecule: str,
    configured: float | Mapping[str, float],
) -> float:
    if isinstance(configured, Mapping):
        if molecule not in configured:
            raise ValueError(f"No pollutant scale height configured for {molecule}.")
        return _positive_scalar(configured[molecule], f"{molecule} scale height")
    return _positive_scalar(configured, "Pollutant scale height")
