"""Machine learning baselines for atmospheric parameter estimation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


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


def make_model_zoo(random_state: int = 7) -> dict[str, Pipeline]:
    """Create a compact model zoo for synthetic regression benchmarks."""
    return {
        "linear": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LinearRegression()),
            ]
        ),
        "ridge_0_1": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=0.1)),
            ]
        ),
        "ridge_1": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        ),
        "ridge_10": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=10.0)),
            ]
        ),
        "ridge_100": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=100.0)),
            ]
        ),
        "lasso_0_0001": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", MultiOutputRegressor(Lasso(alpha=0.0001, max_iter=20_000))),
            ]
        ),
        "elasticnet_0_0001": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", MultiOutputRegressor(ElasticNet(alpha=0.0001, l1_ratio=0.2, max_iter=20_000))),
            ]
        ),
        "pls_8": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", PLSRegression(n_components=8)),
            ]
        ),
        "pls_16": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", PLSRegression(n_components=16)),
            ]
        ),
        "knn_7": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", KNeighborsRegressor(n_neighbors=7, weights="distance")),
            ]
        ),
        "svr_rbf": Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", MultiOutputRegressor(SVR(C=20.0, gamma="scale", epsilon=0.05))),
            ]
        ),
        "random_forest": Pipeline(
            [
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=160,
                        min_samples_leaf=2,
                        max_features=0.45,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            [
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=240,
                        min_samples_leaf=1,
                        max_features=0.65,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def train_model_zoo(
    X: np.ndarray,
    y: np.ndarray,
    random_state: int = 7,
    test_size: float = 0.25,
    model_names: list[str] | None = None,
) -> TrainResult:
    """Train a wider set of estimators for benchmark experiments."""
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )
    models = make_model_zoo(random_state=random_state)
    if model_names is not None:
        models = {name: models[name] for name in model_names}
    for model in models.values():
        model.fit(X_train, y_train)
    return TrainResult(models=models, X_train=X_train, X_test=X_test, y_train=y_train, y_test=y_test)


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    target_names: list[str] | None = None,
) -> pd.DataFrame:
    """Return one row per target with common regression metrics."""
    if target_names is None:
        target_names = TARGET_NAMES
    rows = []
    for target_idx, target_name in enumerate(target_names):
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
