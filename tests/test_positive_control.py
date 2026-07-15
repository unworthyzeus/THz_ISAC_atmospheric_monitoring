from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.positive_control import (  # noqa: E402
    build_h2o_dew_point_sensitivity,
    h2o_positive_control_crb,
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


def _sensitivity():
    return build_h2o_dew_point_sensitivity(
        _processed_hitran_fixture(),
        np.linspace(60.0, 190.0, 32),
        reference_dew_point_c=7.5,
        surface_temperature_k=287.55,
        surface_pressure_pa=101_040.0,
        dew_point_step_c=0.5,
        elevation_deg=45.0,
        spectroscopy_options={
            "n_layers": 2,
            "top_altitude_m": 1_000.0,
            "pollutant_scale_height_m": 800.0,
            "water_scale_height_m": 900.0,
            "pm_scale_height_m": 700.0,
        },
    )


def test_dew_point_finite_difference_has_explicit_consistent_units():
    sensitivity = _sensitivity()
    background_difference = (
        sensitivity.upper_background_db - sensitivity.lower_background_db
    )

    np.testing.assert_allclose(
        sensitivity.dew_point_sensitivity_db_per_c
        * (sensitivity.upper_dew_point_c - sensitivity.lower_dew_point_c),
        background_difference,
        rtol=1.0e-13,
        atol=0.0,
    )
    np.testing.assert_allclose(
        sensitivity.water_vapor_pressure_sensitivity_db_per_pa
        * (
            sensitivity.upper_water_vapor_pressure_pa
            - sensitivity.lower_water_vapor_pressure_pa
        ),
        background_difference,
        rtol=1.0e-13,
        atol=0.0,
    )
    assert sensitivity.frequency_ghz.shape == (32,)
    assert sensitivity.gas_nuisance_db_per_ug_m3.shape == (32, 4)
    assert sensitivity.pm_nuisance_db_per_ug_m3.shape == (32, 2)
    assert np.isfinite(sensitivity.dew_point_sensitivity_db_per_c).all()
    assert np.max(np.abs(sensitivity.dew_point_sensitivity_db_per_c)) > 0.0


def test_positive_control_crb_reports_dew_point_and_vapor_pressure_units():
    sensitivity = _sensitivity()
    variance_db2 = np.full(32, 0.2**2)

    ideal = h2o_positive_control_crb(
        sensitivity,
        variance_db2,
        include_offset_nuisance=False,
        include_pollutant_nuisance=False,
        include_pm_nuisance=False,
    )
    nuisance_aware = h2o_positive_control_crb(sensitivity, variance_db2)
    pressure = h2o_positive_control_crb(
        sensitivity,
        variance_db2,
        target_parameter="water_vapor_pressure_pa",
        include_offset_nuisance=False,
        include_pollutant_nuisance=False,
        include_pm_nuisance=False,
    )

    assert ideal.target_unit == "degC"
    assert pressure.target_unit == "Pa"
    assert ideal.crb.target_identifiable
    assert nuisance_aware.crb.target_identifiable
    assert np.isfinite(nuisance_aware.one_sigma_floor)
    assert nuisance_aware.one_sigma_floor >= ideal.one_sigma_floor
    expected_pa_per_c = (
        sensitivity.upper_water_vapor_pressure_pa
        - sensitivity.lower_water_vapor_pressure_pa
    ) / (sensitivity.upper_dew_point_c - sensitivity.lower_dew_point_c)
    np.testing.assert_allclose(
        pressure.one_sigma_floor / ideal.one_sigma_floor,
        expected_pa_per_c,
        rtol=1.0e-10,
    )
    np.testing.assert_allclose(
        nuisance_aware.three_sigma_floor,
        3.0 * nuisance_aware.one_sigma_floor,
    )


def test_positive_control_supports_physics_only_tone_selection():
    sensitivity = _sensitivity()
    indices = np.arange(0, 32, 2)
    result = h2o_positive_control_crb(
        sensitivity,
        variance_db2=0.1**2,
        selected_indices=indices,
        include_pollutant_nuisance=False,
        include_pm_nuisance=False,
    )

    np.testing.assert_array_equal(result.selected_indices, indices)
    assert result.target_design.shape == (16, 1)
    assert result.nuisance_design.shape == (16, 1)
    with pytest.raises(ValueError, match="duplicates"):
        h2o_positive_control_crb(
            sensitivity,
            variance_db2=0.1**2,
            selected_indices=np.array([0, 0]),
        )


def test_dew_point_perturbation_rejects_out_of_range_endpoints():
    with pytest.raises(ValueError, match="between -80 and 60"):
        build_h2o_dew_point_sensitivity(
            _processed_hitran_fixture(),
            np.linspace(60.0, 190.0, 8),
            reference_dew_point_c=59.9,
            surface_temperature_k=288.15,
            dew_point_step_c=0.2,
            spectroscopy_options={"n_layers": 1, "top_altitude_m": 500.0},
        )
