"""Machine learning baselines for atmospheric parameter estimation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


TARGET_NAMES = ["gas_ppm", "pm_ug_m3"]


@dataclass(frozen=True)
class TrainResult:
    models: dict[str, Pipeline]
    X_train: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray


def train_linear_baselines(
    X: np.ndarray,
    y: np.ndarray,
    random_state: int = 7,
    test_size: float = 0.25,
) -> TrainResult:
    """Train LinearRegression and Ridge baselines."""
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )
    models: dict[str, Pipeline] = {
        "linear_regression": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "ridge_alpha_1": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "ridge_alpha_10": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=10.0)),
            ]
        ),
    }
    for model in models.values():
        model.fit(X_train, y_train)
    return TrainResult(models=models, X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> pd.DataFrame:
    """Return one row per target with common regression metrics."""
    rows = []
    for target_idx, target_name in enumerate(TARGET_NAMES):
        err = y_pred[:, target_idx] - y_true[:, target_idx]
        rows.append(
            {
                "model": model_name,
                "target": target_name,
                "mae": mean_absolute_error(y_true[:, target_idx], y_pred[:, target_idx]),
                "rmse": mean_squared_error(y_true[:, target_idx], y_pred[:, target_idx]) ** 0.5,
                "r2": r2_score(y_true[:, target_idx], y_pred[:, target_idx]),
                "bias": float(np.mean(err)),
            }
        )
    return pd.DataFrame(rows)


def collect_metrics(train_result: TrainResult) -> pd.DataFrame:
    """Evaluate all trained models on the test split."""
    frames = []
    for name, model in train_result.models.items():
        pred = model.predict(train_result.X_test)
        frames.append(evaluate_predictions(train_result.y_test, pred, name))
    return pd.concat(frames, ignore_index=True)

