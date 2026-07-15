from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.constants import Avogadro


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.physical_spectroscopy import (  # noqa: E402
    build_layered_zenith_attenuation_design,
    concentration_ug_m3_to_number_density_cm3,
    rayleigh_mass_extinction_m2_per_kg,
    standard_troposphere_profile,
    voigt_profile_wavenumber,
)


def _processed_hitran_fixture() -> pd.DataFrame:
    molecules = [
        ("H2O", 1, 75.0),
        ("O3", 3, 95.0),
        ("CO", 5, 115.0),
        ("O2", 7, 135.0),
        ("SO2", 9, 155.0),
        ("NO2", 10, 175.0),
    ]
    rows = []
    for index, (symbol, molecule_id, frequency_ghz) in enumerate(molecules):
        rows.append(
            {
                "molecule": symbol,
                "molecule_id": molecule_id,
                "isotopologue_id": 1,
                "role": "background" if symbol in {"H2O", "O2"} else "target",
                "wavenumber_cm_1": frequency_ghz / 29.9792458,
                "frequency_ghz": frequency_ghz,
                "line_intensity": 1.0e-22 * (1.0 + 0.1 * index),
                "einstein_a": 1.0,
                "gamma_air": 0.06,
                "gamma_self": 0.1,
                "lower_state_energy": 1.0 + index,
                "temperature_exponent": 0.7,
                "air_pressure_shift": 0.001,
            }
        )
    return pd.DataFrame(rows)


def _small_design():
    return build_layered_zenith_attenuation_design(
        _processed_hitran_fixture(),
        np.linspace(60.0, 190.0, 24),
        n_layers=4,
        top_altitude_m=2_000.0,
        pollutant_scale_height_m=1_200.0,
        water_scale_height_m=1_800.0,
        pm_scale_height_m=800.0,
    )


def test_concentration_conversion_matches_molecule_count():
    converted = concentration_ug_m3_to_number_density_cm3(1.0, 28.0)
    expected = Avogadro * 1.0e-12 / 28.0

    assert np.isclose(converted, expected, rtol=1.0e-14)


def test_voigt_profile_is_symmetric_and_normalized():
    grid = np.linspace(-8.0, 8.0, 200_001)
    profile = voigt_profile_wavenumber(
        grid,
        center_cm_1=0.0,
        gaussian_sigma_cm_1=0.04,
        lorentz_hwhm_cm_1=0.06,
    )

    assert np.allclose(profile, profile[::-1], rtol=1.0e-12, atol=1.0e-14)
    assert np.isclose(np.trapezoid(profile, grid), 1.0, rtol=6.0e-3)


def test_layered_design_has_nonnegative_finite_physical_shapes():
    design = _small_design()

    assert design.gas_names == ("CO", "O3", "SO2", "NO2")
    assert design.gas_db_per_ug_m3.shape == (24, 4)
    assert design.background_db.shape == (24,)
    assert design.pm_db_per_ug_m3.shape == (24, 2)
    for values in [design.gas_db_per_ug_m3, design.background_db, design.pm_db_per_ug_m3]:
        assert np.isfinite(values).all()
        assert (values >= 0.0).all()
    assert design.gas_db_per_ug_m3.max() > 0.0
    assert design.background_db.max() > 0.0


def test_standard_profile_accepts_uci_surface_medians():
    profile = standard_troposphere_profile(
        n_layers=2,
        top_altitude_m=1_000.0,
        surface_temperature_k=287.55,
        surface_pressure_pa=101_040.0,
    )

    assert np.isclose(profile.temperature_k[0], 287.55 - 0.0065 * 250.0)
    assert profile.pressure_pa[0] < 101_040.0
    assert np.all(np.diff(profile.pressure_pa) < 0.0)


def test_surface_state_propagates_into_layered_background():
    default = build_layered_zenith_attenuation_design(
        _processed_hitran_fixture(),
        np.linspace(60.0, 190.0, 12),
        n_layers=2,
        top_altitude_m=1_000.0,
    )
    uci_median = build_layered_zenith_attenuation_design(
        _processed_hitran_fixture(),
        np.linspace(60.0, 190.0, 12),
        n_layers=2,
        top_altitude_m=1_000.0,
        surface_temperature_k=287.55,
        surface_pressure_pa=101_040.0,
    )

    assert np.isclose(uci_median.atmosphere.temperature_k[0], 287.55 - 0.0065 * 250.0)
    assert not np.allclose(uci_median.background_db, default.background_db, rtol=1.0e-9, atol=0.0)


def test_plane_parallel_path_scaling_doubles_at_thirty_degrees():
    design = _small_design()
    concentrations = {"CO": 500.0, "O3": 50.0, "SO2": 10.0, "NO2": 40.0}
    zenith = design.attenuation_db(
        concentrations,
        pm25_ug_m3=20.0,
        pm10_ug_m3=35.0,
        elevation_deg=90.0,
    )
    slant = design.attenuation_db(
        concentrations,
        pm25_ug_m3=20.0,
        pm10_ug_m3=35.0,
        elevation_deg=30.0,
    )

    assert np.allclose(slant, 2.0 * zenith, rtol=1.0e-12, atol=0.0)


def test_lossless_rayleigh_mass_extinction_follows_frequency_and_size_limits():
    frequencies = np.array([100.0, 200.0])
    one_micrometer = rayleigh_mass_extinction_m2_per_kg(
        frequencies,
        particle_diameter_um=1.0,
        particle_density_kg_m3=1_500.0,
        refractive_index=1.5 + 0.0j,
    )
    two_micrometer = rayleigh_mass_extinction_m2_per_kg(
        frequencies,
        particle_diameter_um=2.0,
        particle_density_kg_m3=1_500.0,
        refractive_index=1.5 + 0.0j,
    )

    assert np.isclose(one_micrometer[1] / one_micrometer[0], 16.0, rtol=1.0e-12)
    assert np.allclose(two_micrometer / one_micrometer, 8.0, rtol=1.0e-12)


def test_pm10_uses_only_mass_above_pm25_for_coarse_mode():
    design = _small_design()
    fine_only = design.attenuation_db(
        pm25_ug_m3=20.0,
        pm10_ug_m3=20.0,
        include_background=False,
    )
    fine_and_coarse = design.attenuation_db(
        pm25_ug_m3=20.0,
        pm10_ug_m3=30.0,
        include_background=False,
    )

    assert np.allclose(fine_only, 20.0 * design.pm_db_per_ug_m3[:, 0])
    assert np.allclose(
        fine_and_coarse - fine_only,
        10.0 * design.pm_db_per_ug_m3[:, 1],
    )
