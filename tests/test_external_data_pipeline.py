from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.external_forward_model import (  # noqa: E402
    ExternalCSIDatasetConfig,
    generate_external_csi_dataset,
    predict_with_template_least_squares,
    template_projection_features,
)
from thz_isac.hitran_templates import hitran_template, rayleigh_pm_template  # noqa: E402


def _hitran_fixture() -> pd.DataFrame:
    rows = []
    molecule_frequencies = {
        "CO": [64.0, 113.0],
        "O3": [72.0, 132.0],
        "SO2": [83.0, 146.0],
        "NO2": [95.0, 158.0],
        "H2O": [105.0, 170.0],
        "O2": [118.0, 190.0],
    }
    for molecule, frequencies in molecule_frequencies.items():
        for idx, frequency in enumerate(frequencies):
            rows.append(
                {
                    "molecule": molecule,
                    "frequency_ghz": frequency,
                    "line_intensity": 1.0 + 0.2 * idx,
                    "gamma_air": 0.08,
                }
            )
    return pd.DataFrame(rows)


def _pollution_fixture() -> pd.DataFrame:
    base = np.arange(1, 9, dtype=float)
    return pd.DataFrame(
        {
            "CO_ug_m3": 500.0 + 80.0 * base,
            "O3_ug_m3": 20.0 + 8.0 * base,
            "SO2_ug_m3": 5.0 + 3.0 * base,
            "NO2_ug_m3": 18.0 + 4.0 * base,
            "PM2_5_ug_m3": 25.0 + 6.0 * base,
            "PM10_ug_m3": 40.0 + 9.0 * base,
        }
    )


def test_hitran_and_pm_templates_are_normalized():
    frequency = np.linspace(60.0, 200.0, 64)
    template = hitran_template(_hitran_fixture(), frequency, "CO")
    pm_template = rayleigh_pm_template(frequency, power=3.2)

    assert template.shape == frequency.shape
    assert pm_template.shape == frequency.shape
    assert np.isclose(template.max(), 1.0)
    assert np.isclose(pm_template.max(), 1.0)
    assert (template >= 0.0).all()
    assert (pm_template >= 0.0).all()


def test_external_csi_dataset_shapes_and_metadata():
    config = ExternalCSIDatasetConfig(
        n_samples=8,
        n_subcarriers=64,
        min_freq_ghz=60.0,
        max_freq_ghz=200.0,
        snr_db_range=(120.0, 120.0),
        random_seed=3,
    )
    dataset = generate_external_csi_dataset(_pollution_fixture(), _hitran_fixture(), config)

    assert dataset.attenuation_db.shape == (8, 64)
    assert dataset.path_normalized_db.shape == (8, 64)
    assert dataset.y.shape == (8, 6)
    assert dataset.design_per_unit.shape == (64, 6)
    assert list(dataset.metadata.columns[-3:]) == ["elevation_deg", "snr_db", "path_factor"]


def test_template_projection_recovers_low_noise_fixture():
    config = ExternalCSIDatasetConfig(
        n_samples=8,
        n_subcarriers=96,
        min_freq_ghz=60.0,
        max_freq_ghz=200.0,
        snr_db_range=(140.0, 140.0),
        background_peak_loss_db=0.02,
        random_seed=11,
    )
    dataset = generate_external_csi_dataset(_pollution_fixture(), _hitran_fixture(), config)
    coeffs = template_projection_features(dataset)
    pred = predict_with_template_least_squares(dataset)

    assert coeffs.shape == (8, 8)
    assert pred.shape == dataset.y.shape
    assert np.mean(np.abs(pred - dataset.y)) < 1e-1
