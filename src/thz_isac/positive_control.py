"""H2O spectroscopy positive control for the physical retrieval pipeline.

This module turns a surface dew point state into a local, layered attenuation
sensitivity using the same HITRAN spectroscopy as the pollutant feasibility
analysis.  The target is either surface dew point in degrees Celsius or water
vapour pressure in pascals.  Both are proxies for a modelled vertical H2O
column with a fixed water scale height; neither is a direct column
measurement.

The reference dew point, temperature, and pressure should be computed from a
training period of the real meteorological data.  They only define the point
where the physical model is linearised and must not be tuned on evaluation
labels or retrieval errors.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from .estimation_bounds import LinearCRBResult, linear_attenuation_crb
from .physical_spectroscopy import (
    REFERENCE_PRESSURE_PA,
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
    water_vapor_pressure_pa_from_dew_point,
)


TargetParameter = Literal["dew_point_c", "water_vapor_pressure_pa"]


@dataclass(frozen=True)
class H2ODewPointSensitivity:
    """Local slant attenuation response to a surface dew point perturbation.

    All attenuation arrays are one way losses in dB.  The finite difference
    columns have units dB per degree Celsius and dB per pascal.  The gas and PM
    columns are retained so the retrieval bound can marginalise over the same
    pollutant nuisance spectra as the main feasibility analysis.
    """

    frequency_ghz: np.ndarray
    reference_dew_point_c: float
    lower_dew_point_c: float
    upper_dew_point_c: float
    reference_surface_temperature_k: float
    reference_surface_pressure_pa: float
    elevation_deg: float
    reference_water_vapor_pressure_pa: float
    lower_water_vapor_pressure_pa: float
    upper_water_vapor_pressure_pa: float
    reference_background_db: np.ndarray
    lower_background_db: np.ndarray
    upper_background_db: np.ndarray
    dew_point_sensitivity_db_per_c: np.ndarray
    water_vapor_pressure_sensitivity_db_per_pa: np.ndarray
    gas_names: tuple[str, ...]
    gas_nuisance_db_per_ug_m3: np.ndarray
    pm_names: tuple[str, ...]
    pm_nuisance_db_per_ug_m3: np.ndarray


@dataclass(frozen=True)
class H2OPositiveControlResult:
    """Nuisance aware CRB for one H2O positive control parameter."""

    target_parameter: TargetParameter
    target_unit: str
    selected_indices: np.ndarray
    target_design: np.ndarray
    nuisance_design: np.ndarray
    nuisance_names: tuple[str, ...]
    crb: LinearCRBResult

    @property
    def one_sigma_floor(self) -> float:
        """Return the local one sigma floor in ``target_unit``."""

        return float(self.crb.target_standard_deviation[0])

    @property
    def three_sigma_floor(self) -> float:
        """Return the local three sigma floor in ``target_unit``."""

        return 3.0 * self.one_sigma_floor


def build_h2o_dew_point_sensitivity(
    hitran_lines: pd.DataFrame,
    frequency_ghz: np.ndarray,
    *,
    reference_dew_point_c: float,
    surface_temperature_k: float,
    surface_pressure_pa: float = REFERENCE_PRESSURE_PA,
    dew_point_step_c: float = 0.25,
    elevation_deg: float = 90.0,
    spectroscopy_options: Mapping[str, object] | None = None,
) -> H2ODewPointSensitivity:
    """Build a central finite difference H2O positive control design.

    The lower, reference, and upper models use identical temperature,
    pressure, frequency, layering, and scale height assumptions.  Only surface
    dew point changes.  Consequently, the derivative captures H2O absorption
    and the small, physical displacement of dry air O2 by water vapour.

    ``spectroscopy_options`` is forwarded to
    :func:`build_layered_zenith_attenuation_design`.  State variables owned by
    this function cannot be overridden there.
    """

    reference_dew_point = _finite_scalar(reference_dew_point_c, "reference_dew_point_c")
    step = _positive_scalar(dew_point_step_c, "dew_point_step_c")
    lower_dew_point = reference_dew_point - step
    upper_dew_point = reference_dew_point + step
    if lower_dew_point < -80.0 or upper_dew_point > 60.0:
        raise ValueError("The central dew point perturbation must remain between -80 and 60 C.")

    temperature = _positive_scalar(surface_temperature_k, "surface_temperature_k")
    pressure = _positive_scalar(surface_pressure_pa, "surface_pressure_pa")
    elevation = _finite_scalar(elevation_deg, "elevation_deg")
    if not 0.0 < elevation <= 90.0:
        raise ValueError("elevation_deg must be in the interval (0, 90].")

    options = dict(spectroscopy_options or {})
    reserved = {
        "surface_dew_point_c",
        "surface_temperature_k",
        "surface_pressure_pa",
    }
    conflicts = reserved.intersection(options)
    if conflicts:
        names = ", ".join(sorted(conflicts))
        raise ValueError(f"spectroscopy_options cannot override: {names}")

    def build(dew_point_c: float):
        return build_layered_zenith_attenuation_design(
            hitran_lines,
            frequency_ghz,
            surface_dew_point_c=dew_point_c,
            surface_temperature_k=temperature,
            surface_pressure_pa=pressure,
            **options,
        )

    lower = build(lower_dew_point)
    reference = build(reference_dew_point)
    upper = build(upper_dew_point)

    lower_background = apply_plane_parallel_slant(lower.background_db, elevation)
    reference_background = apply_plane_parallel_slant(reference.background_db, elevation)
    upper_background = apply_plane_parallel_slant(upper.background_db, elevation)
    background_difference = upper_background - lower_background

    lower_water_pressure = water_vapor_pressure_pa_from_dew_point(lower_dew_point)
    reference_water_pressure = water_vapor_pressure_pa_from_dew_point(reference_dew_point)
    upper_water_pressure = water_vapor_pressure_pa_from_dew_point(upper_dew_point)
    water_pressure_difference = upper_water_pressure - lower_water_pressure
    if not water_pressure_difference > 0.0:
        raise FloatingPointError("Water vapour pressure did not increase with dew point.")

    dew_point_sensitivity = background_difference / (upper_dew_point - lower_dew_point)
    water_pressure_sensitivity = background_difference / water_pressure_difference
    if not np.isfinite(dew_point_sensitivity).all():
        raise FloatingPointError("Nonfinite dew point sensitivity was calculated.")
    if not np.isfinite(water_pressure_sensitivity).all():
        raise FloatingPointError("Nonfinite water vapour pressure sensitivity was calculated.")

    return H2ODewPointSensitivity(
        frequency_ghz=reference.frequency_ghz.copy(),
        reference_dew_point_c=reference_dew_point,
        lower_dew_point_c=lower_dew_point,
        upper_dew_point_c=upper_dew_point,
        reference_surface_temperature_k=temperature,
        reference_surface_pressure_pa=pressure,
        elevation_deg=elevation,
        reference_water_vapor_pressure_pa=reference_water_pressure,
        lower_water_vapor_pressure_pa=lower_water_pressure,
        upper_water_vapor_pressure_pa=upper_water_pressure,
        reference_background_db=reference_background,
        lower_background_db=lower_background,
        upper_background_db=upper_background,
        dew_point_sensitivity_db_per_c=dew_point_sensitivity,
        water_vapor_pressure_sensitivity_db_per_pa=water_pressure_sensitivity,
        gas_names=reference.gas_names,
        gas_nuisance_db_per_ug_m3=apply_plane_parallel_slant(
            reference.gas_db_per_ug_m3,
            elevation,
        ),
        pm_names=reference.pm_names,
        pm_nuisance_db_per_ug_m3=apply_plane_parallel_slant(
            reference.pm_db_per_ug_m3,
            elevation,
        ),
    )


def h2o_positive_control_crb(
    sensitivity: H2ODewPointSensitivity,
    variance_db2: np.ndarray | float,
    *,
    target_parameter: TargetParameter = "dew_point_c",
    selected_indices: np.ndarray | None = None,
    include_offset_nuisance: bool = True,
    include_background_scale_nuisance: bool = False,
    include_pollutant_nuisance: bool = True,
    include_pm_nuisance: bool = True,
    extra_nuisance_design: np.ndarray | None = None,
    rcond: float | None = 1.0e-12,
) -> H2OPositiveControlResult:
    """Return a local H2O retrieval bound with configurable nuisances.

    The default bound treats the UCI temperature and pressure as observed
    conditioning variables.  It marginalises over an additive offset, the
    four pollutant gas spectra, and both PM modes.  Enabling the background
    scale nuisance tests a stricter case with an unknown multiplicative scale
    on the nominal H2O plus O2 background.

    ``variance_db2`` is scalar or has one value per selected tone.  Tone
    selection must be based only on the physical design or a training period,
    never on evaluation retrieval errors.
    """

    n_frequencies = len(sensitivity.frequency_ghz)
    indices = _selected_indices(selected_indices, n_frequencies)
    if target_parameter == "dew_point_c":
        target_column = sensitivity.dew_point_sensitivity_db_per_c[indices]
        target_unit = "degC"
    elif target_parameter == "water_vapor_pressure_pa":
        target_column = sensitivity.water_vapor_pressure_sensitivity_db_per_pa[indices]
        target_unit = "Pa"
    else:
        raise ValueError(
            "target_parameter must be 'dew_point_c' or 'water_vapor_pressure_pa'."
        )

    nuisance_columns: list[np.ndarray] = []
    nuisance_names: list[str] = []
    if include_offset_nuisance:
        nuisance_columns.append(np.ones(len(indices), dtype=float))
        nuisance_names.append("offset")
    if include_background_scale_nuisance:
        nuisance_columns.append(sensitivity.reference_background_db[indices])
        nuisance_names.append("background_scale")
    if include_pollutant_nuisance:
        for column_index, name in enumerate(sensitivity.gas_names):
            nuisance_columns.append(
                sensitivity.gas_nuisance_db_per_ug_m3[indices, column_index]
            )
            nuisance_names.append(name)
    if include_pm_nuisance:
        for column_index, name in enumerate(sensitivity.pm_names):
            nuisance_columns.append(
                sensitivity.pm_nuisance_db_per_ug_m3[indices, column_index]
            )
            nuisance_names.append(name)

    if extra_nuisance_design is not None:
        extra = _selected_extra_nuisance(extra_nuisance_design, indices, n_frequencies)
        for column_index in range(extra.shape[1]):
            nuisance_columns.append(extra[:, column_index])
            nuisance_names.append(f"extra_{column_index}")

    nuisance, retained_names = _normalised_nuisance_design(
        nuisance_columns,
        nuisance_names,
        len(indices),
    )
    crb = linear_attenuation_crb(
        target_column[:, None],
        variance_db2,
        nuisance_design=nuisance if nuisance.shape[1] else None,
        rcond=rcond,
    )
    return H2OPositiveControlResult(
        target_parameter=target_parameter,
        target_unit=target_unit,
        selected_indices=indices,
        target_design=target_column[:, None],
        nuisance_design=nuisance,
        nuisance_names=retained_names,
        crb=crb,
    )


def _selected_indices(value: np.ndarray | None, size: int) -> np.ndarray:
    if value is None:
        return np.arange(size, dtype=int)
    raw = np.asarray(value)
    if raw.ndim != 1 or raw.size == 0:
        raise ValueError("selected_indices must be a nonempty one dimensional array.")
    if not np.issubdtype(raw.dtype, np.integer):
        raise ValueError("selected_indices must contain integers.")
    indices = raw.astype(int, copy=True)
    if np.any(indices < 0) or np.any(indices >= size):
        raise ValueError("selected_indices contains an out of range index.")
    if np.unique(indices).size != indices.size:
        raise ValueError("selected_indices must not contain duplicates.")
    return indices


def _selected_extra_nuisance(
    value: np.ndarray,
    indices: np.ndarray,
    full_size: int,
) -> np.ndarray:
    matrix = np.asarray(value, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix[:, None]
    if matrix.ndim != 2 or matrix.shape[1] < 1 or not np.isfinite(matrix).all():
        raise ValueError("extra_nuisance_design must be a finite one or two dimensional array.")
    if matrix.shape[0] == full_size:
        return matrix[indices]
    if matrix.shape[0] == len(indices):
        return matrix
    raise ValueError(
        "extra_nuisance_design must have one row per full frequency or selected tone."
    )


def _normalised_nuisance_design(
    columns: list[np.ndarray],
    names: list[str],
    n_observations: int,
) -> tuple[np.ndarray, tuple[str, ...]]:
    retained_columns: list[np.ndarray] = []
    retained_names: list[str] = []
    for column, name in zip(columns, names, strict=True):
        values = np.asarray(column, dtype=float)
        if values.shape != (n_observations,) or not np.isfinite(values).all():
            raise ValueError(f"Nuisance column {name} must be finite and match selected tones.")
        norm = float(np.linalg.norm(values))
        if norm > 0.0:
            retained_columns.append(values / norm)
            retained_names.append(name)
    if not retained_columns:
        return np.empty((n_observations, 0), dtype=float), tuple()
    return np.column_stack(retained_columns), tuple(retained_names)


def _finite_scalar(value: float, name: str) -> float:
    scalar = float(value)
    if not np.isfinite(scalar):
        raise ValueError(f"{name} must be finite.")
    return scalar


def _positive_scalar(value: float, name: str) -> float:
    scalar = _finite_scalar(value, name)
    if scalar <= 0.0:
        raise ValueError(f"{name} must be strictly positive.")
    return scalar
