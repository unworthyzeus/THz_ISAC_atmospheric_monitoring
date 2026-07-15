from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.measured_thz_control import (  # noqa: E402
    evaluate_high_band_control,
    frequency_monotonicity_table,
    read_concentration_spectrum_csv,
)


def _write_fixture(path: Path, *, negative_sd: bool = False) -> Path:
    sd = -1.0 if negative_sd else 1.0
    path.write_text(
        "A,D,E,F,G\n"
        "Concentration (mg/mL),0.8 THz,SD1,1.0THz,SD2\n"
        f"0,10,{sd},20,1\n"
        "10,9,1,18,1\n"
        "20,8,1,16,1\n"
        "30,7,1,14,1\n",
        encoding="utf-8",
    )
    return path


def test_parser_preserves_concentration_levels_and_mean_sd_pairs(tmp_path: Path):
    data = read_concentration_spectrum_csv(
        _write_fixture(tmp_path / "fixture.csv"),
        analyte="control",
    )

    np.testing.assert_allclose(data.concentration_mg_ml, [0.0, 10.0, 20.0, 30.0])
    np.testing.assert_allclose(data.frequency_thz, [0.8, 1.0])
    assert data.absorption_coefficient.shape == (4, 2)
    assert data.absorption_sd.shape == (4, 2)


def test_fixed_high_band_control_detects_perfect_decreasing_monotonicity(
    tmp_path: Path,
):
    data = read_concentration_spectrum_csv(
        _write_fixture(tmp_path / "fixture.csv"),
        analyte="control",
    )
    result = evaluate_high_band_control(data, band_min_thz=0.9)

    assert result.band_frequency_count == 1
    assert result.spearman_rho == pytest.approx(-1.0)
    assert result.loocv_rmse_mg_ml == pytest.approx(0.0, abs=1.0e-10)
    assert result.loocv_q05_q95_nrmse == pytest.approx(0.0, abs=1.0e-10)


def test_frequency_table_is_descriptive_and_does_not_select_a_channel(tmp_path: Path):
    data = read_concentration_spectrum_csv(
        _write_fixture(tmp_path / "fixture.csv"),
        analyte="control",
    )
    table = frequency_monotonicity_table(data)

    assert len(table) == 2
    assert set(table["selection_role"]) == {"descriptive_only"}
    np.testing.assert_allclose(table["spearman_rho"], [-1.0, -1.0])


def test_parser_rejects_negative_reported_standard_deviation(tmp_path: Path):
    with pytest.raises(ValueError, match="nonnegative"):
        read_concentration_spectrum_csv(
            _write_fixture(tmp_path / "fixture.csv", negative_sd=True),
            analyte="control",
        )
