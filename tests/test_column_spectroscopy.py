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

from thz_isac.column_spectroscopy import (  # noqa: E402
    ColumnDomain,
    GasColumnKey,
    GasColumnProfile,
    build_column_attenuation_design,
)
from thz_isac.physical_spectroscopy import (  # noqa: E402
    DB_PER_NEPER,
    AtmosphereProfile,
    molecular_cross_section_cm2_per_molecule,
    standard_troposphere_profile,
)


def _processed_hitran_fixture() -> pd.DataFrame:
    rows = []
    for index, (symbol, molecule_id, frequency_ghz) in enumerate(
        [("CO", 5, 115.0), ("NO2", 10, 175.0)]
    ):
        rows.append(
            {
                "molecule": symbol,
                "molecule_id": molecule_id,
                "isotopologue_id": 1,
                "role": "target",
                "wavenumber_cm_1": frequency_ghz / 29.9792458,
                "frequency_ghz": frequency_ghz,
                "line_intensity": 1.0e-22 * (1.0 + 0.2 * index),
                "einstein_a": 1.0,
                "gamma_air": 0.06,
                "gamma_self": 0.1,
                "lower_state_energy": 2.0 + index,
                "temperature_exponent": 0.7,
                "air_pressure_shift": 0.001,
            }
        )
    return pd.DataFrame(rows)


def _atmosphere() -> AtmosphereProfile:
    return standard_troposphere_profile(
        n_layers=3,
        top_altitude_m=3_000.0,
        surface_temperature_k=287.55,
        surface_pressure_pa=101_040.0,
    )


def _explicit_profiles() -> tuple[GasColumnProfile, GasColumnProfile]:
    return (
        GasColumnProfile(
            molecule="CO",
            column_domain=ColumnDomain.TOTAL_COLUMN,
            normalized_layer_weights=np.array([0.2, 0.3, 0.5]),
        ),
        GasColumnProfile(
            molecule="NO2",
            column_domain=ColumnDomain.TROPOSPHERIC_COLUMN,
            normalized_layer_weights=np.array([0.65, 0.30, 0.05]),
        ),
    )


def test_column_coefficient_times_column_closes_direct_layer_optical_depth():
    atmosphere = _atmosphere()
    frequency = np.array([110.0, 115.0, 170.0, 175.0])
    profiles = _explicit_profiles()
    design = build_column_attenuation_design(
        _processed_hitran_fixture(),
        frequency,
        profiles,
        atmosphere=atmosphere,
    )
    columns = {
        GasColumnKey("CO", ColumnDomain.TOTAL_COLUMN): 1.7e18,
        GasColumnKey("NO2", ColumnDomain.TROPOSPHERIC_COLUMN): 2.4e15,
    }

    coefficient_result = design.attenuation_db(columns)
    layer_result = design.direct_layer_attenuation_db(columns)
    manual_optical_depth = np.zeros(frequency.size)
    for profile in profiles:
        column = columns[profile.key]
        for layer_index, (temperature_k, pressure_pa) in enumerate(
            zip(atmosphere.temperature_k, atmosphere.pressure_pa, strict=True)
        ):
            cross_section = molecular_cross_section_cm2_per_molecule(
                _processed_hitran_fixture(),
                frequency,
                profile.molecule,
                temperature_k=float(temperature_k),
                pressure_pa=float(pressure_pa),
            )
            manual_optical_depth += (
                cross_section
                * column
                * profile.normalized_layer_weights[layer_index]
            )

    np.testing.assert_allclose(coefficient_result, layer_result, rtol=2.0e-15)
    np.testing.assert_allclose(
        coefficient_result,
        DB_PER_NEPER * manual_optical_depth,
        rtol=2.0e-15,
    )
    assert design.attenuation_db_per_molecule_cm2.shape == (4, 2)
    assert design.layer_cross_section_cm2_per_molecule.shape == (3, 4, 2)
    assert np.isfinite(design.attenuation_db_per_molecule_cm2).all()
    assert np.all(design.attenuation_db_per_molecule_cm2 >= 0.0)


def test_co_total_and_no2_tropospheric_domains_remain_explicit_and_distinct():
    design = build_column_attenuation_design(
        _processed_hitran_fixture(),
        np.array([115.0, 175.0]),
        _explicit_profiles(),
        atmosphere=_atmosphere(),
    )

    assert design.column_keys == (
        GasColumnKey("CO", ColumnDomain.TOTAL_COLUMN),
        GasColumnKey("NO2", ColumnDomain.TROPOSPHERIC_COLUMN),
    )
    assert design.gas_names == ("CO", "NO2")
    assert design.column_domains == (
        ColumnDomain.TOTAL_COLUMN,
        ColumnDomain.TROPOSPHERIC_COLUMN,
    )
    with pytest.raises(ValueError, match="Column domain mismatch for CO"):
        design.attenuation_db(
            {GasColumnKey("CO", ColumnDomain.TROPOSPHERIC_COLUMN): 1.0e18}
        )
    with pytest.raises(TypeError, match="GasColumnKey"):
        design.attenuation_db({"CO": 1.0e18})


def test_exponential_scale_height_generates_normalized_midpoint_weights():
    atmosphere = _atmosphere()
    scale_height_m = 1_500.0
    design = build_column_attenuation_design(
        _processed_hitran_fixture(),
        np.array([112.0, 115.0]),
        (
            GasColumnProfile(
                molecule="CO",
                column_domain="total_column",
                scale_height_m=scale_height_m,
            ),
        ),
        atmosphere=atmosphere,
    )
    expected = (
        np.exp(-atmosphere.altitude_m / scale_height_m)
        * atmosphere.layer_thickness_m
    )
    expected /= expected.sum()

    np.testing.assert_allclose(
        design.normalized_layer_weights[:, 0],
        expected,
        rtol=1.0e-15,
    )
    np.testing.assert_allclose(design.normalized_layer_weights.sum(axis=0), 1.0)
    layer_columns = design.layer_columns_molecules_cm2(
        {GasColumnKey("CO", "total_column"): 1.25e18}
    )
    np.testing.assert_allclose(layer_columns.sum(axis=0), [1.25e18])


@pytest.mark.parametrize(
    ("profile", "message"),
    [
        (
            GasColumnProfile("CO", "total_column"),
            "exactly one",
        ),
        (
            GasColumnProfile(
                "CO",
                "total_column",
                normalized_layer_weights=np.array([0.2, 0.3, 0.5]),
                scale_height_m=1_000.0,
            ),
            "exactly one",
        ),
        (
            GasColumnProfile(
                "CO",
                "total_column",
                normalized_layer_weights=np.array([0.2, 0.3, 0.4]),
            ),
            "sum to one",
        ),
        (
            GasColumnProfile(
                "CO",
                "total_column",
                normalized_layer_weights=np.array([0.5, -0.1, 0.6]),
            ),
            "nonnegative",
        ),
        (
            GasColumnProfile(
                "CO",
                "total_column",
                normalized_layer_weights=np.array([0.5, 0.5]),
            ),
            "shape",
        ),
        (
            GasColumnProfile("CO", "total_column", scale_height_m=0.0),
            "positive",
        ),
    ],
)
def test_profile_contract_rejects_ambiguous_or_invalid_vertical_shapes(
    profile: GasColumnProfile,
    message: str,
):
    with pytest.raises(ValueError, match=message):
        build_column_attenuation_design(
            _processed_hitran_fixture(),
            np.array([115.0]),
            (profile,),
            atmosphere=_atmosphere(),
        )


def test_design_rejects_duplicate_molecule_domains_and_invalid_columns():
    profiles = (
        GasColumnProfile("CO", "total_column", scale_height_m=2_000.0),
        GasColumnProfile("CO", "tropospheric_column", scale_height_m=1_000.0),
    )
    with pytest.raises(ValueError, match="only once"):
        build_column_attenuation_design(
            _processed_hitran_fixture(),
            np.array([115.0]),
            profiles,
            atmosphere=_atmosphere(),
        )

    design = build_column_attenuation_design(
        _processed_hitran_fixture(),
        np.array([115.0]),
        (GasColumnProfile("CO", "total_column", scale_height_m=2_000.0),),
        atmosphere=_atmosphere(),
    )
    for invalid in [-1.0, np.nan, np.inf]:
        with pytest.raises(ValueError, match="finite and nonnegative"):
            design.attenuation_db({GasColumnKey("CO", "total_column"): invalid})


def test_atmosphere_layers_are_validated_before_spectroscopy():
    invalid_atmosphere = AtmosphereProfile(
        altitude_m=np.array([500.0, 1_500.0]),
        layer_thickness_m=np.array([1_000.0]),
        temperature_k=np.array([285.0, 278.0]),
        pressure_pa=np.array([95_000.0, 84_000.0]),
    )
    with pytest.raises(ValueError, match="same nonzero length"):
        build_column_attenuation_design(
            _processed_hitran_fixture(),
            np.array([115.0]),
            (GasColumnProfile("CO", "total_column", scale_height_m=2_000.0),),
            atmosphere=invalid_atmosphere,
        )
