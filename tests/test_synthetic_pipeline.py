from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.estimators import train_linear_baselines
from thz_isac.features import build_features
from thz_isac.physics_estimator import TemplateLeastSquaresEstimator
from thz_isac.synthetic_data import SyntheticDatasetConfig, generate_dataset


def test_generate_dataset_shapes():
    dataset = generate_dataset(SyntheticDatasetConfig(n_samples=64, n_subcarriers=32))
    assert dataset.X.shape == (64, 32)
    assert dataset.y.shape == (64, 2)
    assert len(dataset.frequency_ghz) == 32


def test_train_linear_baseline():
    dataset = generate_dataset(SyntheticDatasetConfig(n_samples=128, n_subcarriers=48))
    result = train_linear_baselines(dataset.X, dataset.y)
    assert "linear_regression" in result.models
    assert result.X_test.shape[0] > 0


def test_path_normalized_features_shape():
    dataset = generate_dataset(SyntheticDatasetConfig(n_samples=64, n_subcarriers=32))
    features = build_features(dataset, "path_normalized")
    assert features.shape == (64, 32)


def test_template_least_squares_predicts_targets():
    dataset = generate_dataset(SyntheticDatasetConfig(n_samples=64, n_subcarriers=32))
    estimator = TemplateLeastSquaresEstimator(dataset.frequency_ghz)
    pred = estimator.predict_from_attenuation(
        dataset.attenuation_db,
        dataset.metadata["elevation_deg"].to_numpy(),
    )
    assert pred.shape == (64, 2)
    assert (pred >= 0.0).all()
