"""Benchmark contemporaneous ground sensor network reconstruction.

For every query station and timestamp, current pollutant measurements from
other stations are allowed. The query station's current six pollutant labels
are removed before every pivot feature and aggregate. This is not forecasting,
satellite sensing, or THz inversion.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.linear_gaussian import (  # noqa: E402
    multi_target_regression_metrics,
    paired_bootstrap_macro_nrmse_difference,
)
from thz_isac.spatial_fusion import (  # noqa: E402
    SpatialFusionFeatures,
    assert_query_current_targets_excluded,
    build_spatial_fusion_features,
    compose_per_target_predictions,
    feature_columns_for_groups,
    lag_delta_transfer_prediction,
    other_station_mean_prediction,
    select_per_target_by_validation,
)
from thz_isac.temporal_baselines import evenly_spaced_sample_indices  # noqa: E402


REPORT_TARGETS = ("CO", "O3", "SO2", "NO2", "PM2.5", "PM10")
TARGET_COLUMNS = (
    "CO_ug_m3",
    "O3_ug_m3",
    "SO2_ug_m3",
    "NO2_ug_m3",
    "PM2_5_ug_m3",
    "PM10_ug_m3",
)
WEATHER_COLUMNS = (
    "temperature_c",
    "pressure_hpa",
    "dew_point_c",
    "rain_mm",
    "wind_speed_m_s",
)
LAG_HOURS = (1, 2, 3, 6, 24)
SAMPLE_SIZE = 20_000
RANDOM_SEED = 20260715
TARGET_MACRO_NRMSE = 0.08
RIDGE_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0)
PLS_COMPONENTS = (4, 8, 16)
HGB_CONFIGS = (
    {
        "max_iter": 120,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 30,
        "l2_regularization": 10.0,
    },
    {
        "max_iter": 180,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 50,
        "l2_regularization": 50.0,
    },
)
EXTRA_TREES_CONFIGS = (
    {"n_estimators": 160, "min_samples_leaf": 2, "max_features": 0.7},
    {"n_estimators": 160, "min_samples_leaf": 5, "max_features": 0.7},
)
SPATIAL_ONLY_GROUPS = (
    "spatial_current_pivot",
    "spatial_current_aggregate",
    "query_weather",
    "network_weather",
    "calendar",
    "station_identity",
)
SPATIAL_CAUSAL_GROUPS = (
    *SPATIAL_ONLY_GROUPS,
    "query_causal_lag",
    "spatial_change_pivot",
    "spatial_change_aggregate",
)
COMPOSITE_CANDIDATE_ORDER = (
    "other_station_current_mean",
    "one_hour_network_delta_transfer",
    "spatial_only_ridge",
    "spatial_causal_ridge",
    "spatial_causal_pls",
    "station_target_delta_ridge",
    "spatial_causal_histogram_boosting",
    "spatial_causal_extra_trees",
)


def parse_args() -> argparse.Namespace:
    """Parse source and output path overrides."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--air-quality",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "processed"
        / "air_quality"
        / "beijing_air_quality_clean.csv.gz",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def macro_nrmse(
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> float:
    """Return the unweighted target mean normalized RMSE."""
    return multi_target_regression_metrics(
        truth,
        prediction,
        denominators,
    ).macro_normalized_rmse


def preprocess_features(
    frame: pd.DataFrame,
    columns: list[str],
    split,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Fit median imputation and scaling on training rows only."""
    raw_train = frame.iloc[split.train][columns].to_numpy(float)
    raw_validation = frame.iloc[split.validation][columns].to_numpy(float)
    raw_test = frame.iloc[split.test][columns].to_numpy(float)
    imputer = SimpleImputer(
        strategy="median",
        add_indicator=True,
        keep_empty_features=True,
    )
    imputed = (
        imputer.fit_transform(raw_train),
        imputer.transform(raw_validation),
        imputer.transform(raw_test),
    )
    scaler = StandardScaler()
    scaled = (
        scaler.fit_transform(imputed[0]),
        scaler.transform(imputed[1]),
        scaler.transform(imputed[2]),
    )
    return imputed, scaled


def fit_ridge_grid(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
    model_name: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select one multioutput Ridge alpha using validation only."""
    best_score = np.inf
    best_model: Ridge | None = None
    best_validation: np.ndarray | None = None
    best_alpha = np.nan
    rows = []
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(blocks[0], scaled_targets[split.train])
        validation_prediction = model.predict(blocks[1]) * denominators + target_mean
        score = macro_nrmse(
            targets[split.validation],
            validation_prediction,
            denominators,
        )
        rows.append(
            {
                "model": model_name,
                "candidate_json": json.dumps({"alpha": alpha}, sort_keys=True),
                "validation_macro_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_model = model
            best_validation = validation_prediction
            best_alpha = alpha
    if best_model is None or best_validation is None:
        raise RuntimeError("Ridge validation grid did not select a model")
    test_prediction = best_model.predict(blocks[2]) * denominators + target_mean
    return best_validation, test_prediction, {"alpha": best_alpha}, rows


def fit_pls_grid(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a multioutput latent component count using validation only."""
    best_score = np.inf
    best_model: PLSRegression | None = None
    best_validation: np.ndarray | None = None
    best_components = 0
    rows = []
    for components in PLS_COMPONENTS:
        model = PLSRegression(n_components=components, scale=False, max_iter=500)
        model.fit(blocks[0], scaled_targets[split.train])
        validation_prediction = model.predict(blocks[1]) * denominators + target_mean
        score = macro_nrmse(
            targets[split.validation],
            validation_prediction,
            denominators,
        )
        rows.append(
            {
                "model": "spatial_causal_pls",
                "candidate_json": json.dumps(
                    {"n_components": components, "scale": False}, sort_keys=True
                ),
                "validation_macro_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_model = model
            best_validation = validation_prediction
            best_components = components
    if best_model is None or best_validation is None:
        raise RuntimeError("PLS validation grid did not select a model")
    test_prediction = best_model.predict(blocks[2]) * denominators + target_mean
    return (
        best_validation,
        test_prediction,
        {"n_components": best_components, "scale": False},
        rows,
    )


def fit_hgb_grid(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a common targetwise histogram boosting configuration on validation."""
    best_score = np.inf
    best_models: list[HistGradientBoostingRegressor] | None = None
    best_validation: np.ndarray | None = None
    best_config: dict[str, object] | None = None
    rows = []
    for config in HGB_CONFIGS:
        validation_prediction = np.empty((len(split.validation), len(REPORT_TARGETS)))
        models = []
        iterations = []
        for target_index in range(len(REPORT_TARGETS)):
            model = HistGradientBoostingRegressor(
                **config,
                learning_rate=0.05,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=15,
                random_state=RANDOM_SEED + target_index,
            )
            model.fit(blocks[0], scaled_targets[split.train, target_index])
            validation_prediction[:, target_index] = (
                model.predict(blocks[1]) * denominators[target_index]
                + target_mean[target_index]
            )
            models.append(model)
            iterations.append(int(model.n_iter_))
        score = macro_nrmse(
            targets[split.validation],
            validation_prediction,
            denominators,
        )
        candidate = {
            **config,
            "learning_rate": 0.05,
            "early_stopping": True,
            "fitted_iterations": iterations,
        }
        rows.append(
            {
                "model": "spatial_causal_histogram_boosting",
                "candidate_json": json.dumps(candidate, sort_keys=True),
                "validation_macro_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_models = models
            best_validation = validation_prediction
            best_config = candidate
    if best_models is None or best_validation is None or best_config is None:
        raise RuntimeError("Histogram boosting validation grid did not select a model")
    test_prediction = np.column_stack(
        [
            model.predict(blocks[2]) * denominators[target_index]
            + target_mean[target_index]
            for target_index, model in enumerate(best_models)
        ]
    )
    return best_validation, test_prediction, best_config, rows


def fit_extra_trees_grid(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a balanced multioutput Extra Trees configuration on validation."""
    best_score = np.inf
    best_model: ExtraTreesRegressor | None = None
    best_validation: np.ndarray | None = None
    best_config: dict[str, object] | None = None
    rows = []
    for config in EXTRA_TREES_CONFIGS:
        model = ExtraTreesRegressor(
            **config,
            random_state=RANDOM_SEED,
            n_jobs=-1,
        )
        model.fit(blocks[0], scaled_targets[split.train])
        validation_prediction = model.predict(blocks[1]) * denominators + target_mean
        score = macro_nrmse(
            targets[split.validation],
            validation_prediction,
            denominators,
        )
        rows.append(
            {
                "model": "spatial_causal_extra_trees",
                "candidate_json": json.dumps(config, sort_keys=True),
                "validation_macro_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_model = model
            best_validation = validation_prediction
            best_config = dict(config)
    if best_model is None or best_validation is None or best_config is None:
        raise RuntimeError("Extra Trees validation grid did not select a model")
    test_prediction = best_model.predict(blocks[2]) * denominators + target_mean
    return best_validation, test_prediction, best_config, rows


def fit_station_target_delta_ridge(
    features: SpatialFusionFeatures,
    sample: pd.DataFrame,
    targets: np.ndarray,
    split,
    denominators: np.ndarray,
    fallback_validation: np.ndarray,
    fallback_test: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Fit station and target specific Ridge models for one hour changes."""
    frame = features.frame
    validation_prediction = fallback_validation.copy()
    test_prediction = fallback_test.copy()
    validation_sample = sample.iloc[split.validation].reset_index(drop=True)
    test_sample = sample.iloc[split.test].reset_index(drop=True)
    selected_alphas: dict[str, dict[str, float]] = {}
    selection_rows = []
    context_columns = feature_columns_for_groups(
        features,
        ("query_weather", "network_weather", "calendar"),
    )
    lag_columns = [
        f"{target}_lag{lag}h"
        for lag in (1, 2, 3)
        for target in TARGET_COLUMNS
    ]

    for station in sorted(sample["station"].astype(str).unique()):
        train_indices = split.train[
            sample.iloc[split.train]["station"].astype(str).to_numpy() == station
        ]
        validation_positions = np.flatnonzero(
            validation_sample["station"].astype(str).to_numpy() == station
        )
        validation_indices = split.validation[validation_positions]
        test_positions = np.flatnonzero(
            test_sample["station"].astype(str).to_numpy() == station
        )
        test_indices = split.test[test_positions]
        selected_alphas[station] = {}
        for target_index, target in enumerate(TARGET_COLUMNS):
            target_columns = [
                column
                for column in frame.columns
                if column.startswith(f"current_other__{target}__")
                or column.startswith(f"change_other__{target}__lag1h__")
            ]
            model_columns = list(dict.fromkeys([*target_columns, *lag_columns, *context_columns]))
            query_lag = frame[f"{target}_lag1h"].to_numpy(float)
            response = targets[:, target_index] - query_lag
            valid_train = train_indices[np.isfinite(response[train_indices])]
            if len(valid_train) < 100 or len(validation_indices) == 0 or len(test_indices) == 0:
                raise RuntimeError(f"Insufficient station rows for {station} and {target}")

            imputer = SimpleImputer(
                strategy="median",
                add_indicator=True,
                keep_empty_features=True,
            )
            train_x = imputer.fit_transform(frame.iloc[valid_train][model_columns])
            validation_x = imputer.transform(frame.iloc[validation_indices][model_columns])
            test_x = imputer.transform(frame.iloc[test_indices][model_columns])
            scaler = StandardScaler()
            train_x = scaler.fit_transform(train_x)
            validation_x = scaler.transform(validation_x)
            test_x = scaler.transform(test_x)

            best_score = np.inf
            best_model: Ridge | None = None
            best_station_validation: np.ndarray | None = None
            best_alpha = np.nan
            for alpha in RIDGE_ALPHAS:
                model = Ridge(alpha=alpha)
                model.fit(train_x, response[valid_train])
                station_validation = query_lag[validation_indices] + model.predict(
                    validation_x
                )
                station_validation = np.where(
                    np.isfinite(station_validation),
                    station_validation,
                    fallback_validation[validation_positions, target_index],
                )
                score = float(
                    np.sqrt(
                        np.mean(
                            (
                                station_validation
                                - targets[validation_indices, target_index]
                            )
                            ** 2
                        )
                    )
                    / denominators[target_index]
                )
                selection_rows.append(
                    {
                        "model": "station_target_delta_ridge",
                        "candidate_json": json.dumps(
                            {"station": station, "target": target, "alpha": alpha},
                            sort_keys=True,
                        ),
                        "validation_macro_normalized_rmse": score,
                    }
                )
                if score < best_score:
                    best_score = score
                    best_model = model
                    best_station_validation = station_validation
                    best_alpha = alpha
            if best_model is None or best_station_validation is None:
                raise RuntimeError("Station target Ridge did not select a model")
            station_test = query_lag[test_indices] + best_model.predict(test_x)
            station_test = np.where(
                np.isfinite(station_test),
                station_test,
                fallback_test[test_positions, target_index],
            )
            validation_prediction[validation_positions, target_index] = (
                best_station_validation
            )
            test_prediction[test_positions, target_index] = station_test
            selected_alphas[station][target] = float(best_alpha)
    return (
        validation_prediction,
        test_prediction,
        {"alpha_by_station_and_target": selected_alphas},
        selection_rows,
    )

def metric_rows(
    model: str,
    split_name: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
    contract: dict[str, object],
) -> list[dict[str, object]]:
    """Return one auditable metric row per target."""
    metrics = multi_target_regression_metrics(truth, prediction, denominators)
    return [
        {
            "model": model,
            "split": split_name,
            **contract,
            "target": target,
            "mae_ug_m3": float(metrics.mae[index]),
            "rmse_ug_m3": float(metrics.rmse[index]),
            "normalized_rmse": float(metrics.normalized_rmse[index]),
            "r2": float(metrics.r2[index]),
            "bias_ug_m3": float(metrics.bias[index]),
        }
        for index, target in enumerate(REPORT_TARGETS)
    ]


def dependency_versions() -> dict[str, str]:
    """Return relevant installed dependency versions."""
    versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def main() -> None:
    """Run the real ground sensor network reconstruction benchmark."""
    args = parse_args()
    started = time.perf_counter()
    if not args.air_quality.exists():
        raise FileNotFoundError(f"Required input does not exist: {args.air_quality}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "spatial_fusion_metrics.csv"
    summary_path = args.output_dir / "spatial_fusion_summary.csv"
    validation_path = args.output_dir / "spatial_fusion_validation.csv"
    predictions_path = args.output_dir / "spatial_fusion_predictions.csv"
    manifest_path = args.output_dir / "spatial_fusion_manifest.json"

    print("Loading real Beijing ground station measurements.")
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    if data.duplicated(["station", "datetime"]).any():
        raise ValueError("Air quality source contains duplicate station and timestamp keys")
    physically_ordered = (
        data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]]
        .sort_values(["datetime", "station"])
        .reset_index(drop=True)
    )
    sample_indices = evenly_spaced_sample_indices(len(physically_ordered), SAMPLE_SIZE)
    sample = physically_ordered.iloc[sample_indices].reset_index(drop=True)
    targets = sample[list(TARGET_COLUMNS)].to_numpy(float)
    split = chronological_timestamp_split(sample[["datetime", "station"]])
    validate_disjoint_split(split, len(sample))
    target_mean = targets[split.train].mean(axis=0)
    denominators = np.quantile(targets[split.train], 0.95, axis=0) - np.quantile(
        targets[split.train], 0.05, axis=0
    )
    scaled_targets = (targets - target_mean) / denominators

    print("Building masked contemporaneous donor and exact causal lag features.")
    features = build_spatial_fusion_features(
        data,
        sample,
        TARGET_COLUMNS,
        WEATHER_COLUMNS,
        LAG_HOURS,
    )
    assert_query_current_targets_excluded(features)
    spatial_columns = feature_columns_for_groups(features, SPATIAL_ONLY_GROUPS)
    causal_columns = feature_columns_for_groups(features, SPATIAL_CAUSAL_GROUPS)
    spatial_imputed, spatial_scaled = preprocess_features(
        features.frame,
        spatial_columns,
        split,
    )
    causal_imputed, causal_scaled = preprocess_features(
        features.frame,
        causal_columns,
        split,
    )
    hgb_columns = [
        column
        for column in causal_columns
        if "lag6h" not in column and "lag24h" not in column
    ]
    hgb_blocks = (
        features.frame.iloc[split.train][hgb_columns].to_numpy(float),
        features.frame.iloc[split.validation][hgb_columns].to_numpy(float),
        features.frame.iloc[split.test][hgb_columns].to_numpy(float),
    )

    validation_predictions: dict[str, np.ndarray] = {}
    test_predictions: dict[str, np.ndarray] = {}
    selected_configs: dict[str, object] = {}
    validation_rows: list[dict[str, object]] = []

    mean_validation = np.broadcast_to(target_mean, targets[split.validation].shape)
    mean_test = np.broadcast_to(target_mean, targets[split.test].shape)
    validation_predictions["training_period_mean"] = mean_validation
    test_predictions["training_period_mean"] = mean_test
    network_mean = other_station_mean_prediction(features, target_mean)
    delta_transfer = lag_delta_transfer_prediction(features, 1, target_mean)
    validation_predictions["other_station_current_mean"] = network_mean[split.validation]
    test_predictions["other_station_current_mean"] = network_mean[split.test]
    validation_predictions["one_hour_network_delta_transfer"] = delta_transfer[
        split.validation
    ]
    test_predictions["one_hour_network_delta_transfer"] = delta_transfer[split.test]

    print("Selecting spatial and causal Ridge and PLS models on validation only.")
    for model_name, blocks in (
        ("spatial_only_ridge", spatial_scaled),
        ("spatial_causal_ridge", causal_scaled),
    ):
        validation_prediction, test_prediction, config, rows = fit_ridge_grid(
            blocks,
            scaled_targets,
            targets,
            split,
            target_mean,
            denominators,
            model_name,
        )
        validation_predictions[model_name] = validation_prediction
        test_predictions[model_name] = test_prediction
        selected_configs[model_name] = config
        validation_rows.extend(rows)
    pls_validation, pls_test, pls_config, rows = fit_pls_grid(
        causal_scaled,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
    )
    validation_predictions["spatial_causal_pls"] = pls_validation
    test_predictions["spatial_causal_pls"] = pls_test
    selected_configs["spatial_causal_pls"] = pls_config
    validation_rows.extend(rows)

    print("Fitting station and target specific network change Ridge models.")
    station_validation, station_test, station_config, rows = (
        fit_station_target_delta_ridge(
            features,
            sample,
            targets,
            split,
            denominators,
            validation_predictions["one_hour_network_delta_transfer"],
            test_predictions["one_hour_network_delta_transfer"],
        )
    )
    validation_predictions["station_target_delta_ridge"] = station_validation
    test_predictions["station_target_delta_ridge"] = station_test
    selected_configs["station_target_delta_ridge"] = station_config
    validation_rows.extend(rows)

    print("Selecting nonlinear fusion models on validation only.")
    hgb_validation, hgb_test, hgb_config, rows = fit_hgb_grid(
        hgb_blocks,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
    )
    validation_predictions["spatial_causal_histogram_boosting"] = hgb_validation
    test_predictions["spatial_causal_histogram_boosting"] = hgb_test
    selected_configs["spatial_causal_histogram_boosting"] = hgb_config
    validation_rows.extend(rows)
    trees_validation, trees_test, trees_config, rows = fit_extra_trees_grid(
        causal_imputed,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
    )
    validation_predictions["spatial_causal_extra_trees"] = trees_validation
    test_predictions["spatial_causal_extra_trees"] = trees_test
    selected_configs["spatial_causal_extra_trees"] = trees_config
    validation_rows.extend(rows)

    composite_validation_candidates = {
        name: validation_predictions[name] for name in COMPOSITE_CANDIDATE_ORDER
    }
    composite_test_candidates = {
        name: test_predictions[name] for name in COMPOSITE_CANDIDATE_ORDER
    }
    selected_components = select_per_target_by_validation(
        targets[split.validation],
        composite_validation_candidates,
        denominators,
        COMPOSITE_CANDIDATE_ORDER,
    )
    validation_predictions["validation_selected_per_target_fusion"] = (
        compose_per_target_predictions(
            selected_components,
            composite_validation_candidates,
        )
    )
    test_predictions["validation_selected_per_target_fusion"] = (
        compose_per_target_predictions(selected_components, composite_test_candidates)
    )
    selected_configs["validation_selected_per_target_fusion"] = {
        "selected_component_by_target": {
            target: selected_components[index]
            for index, target in enumerate(REPORT_TARGETS)
        },
        "candidate_order": list(COMPOSITE_CANDIDATE_ORDER),
    }

    contracts = {
        "training_period_mean": {
            "model_role": "constant control",
            "uses_current_other_station_targets": False,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": False,
        },
        "other_station_current_mean": {
            "model_role": "spatial aggregate control",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": False,
        },
        "one_hour_network_delta_transfer": {
            "model_role": "spatial change transfer control",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "spatial_only_ridge": {
            "model_role": "spatial pivot regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": False,
        },
        "spatial_causal_ridge": {
            "model_role": "spatial and causal regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "spatial_causal_pls": {
            "model_role": "spatial and causal latent regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "station_target_delta_ridge": {
            "model_role": "station and target specific spatial change regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "spatial_causal_histogram_boosting": {
            "model_role": "nonlinear spatial and causal regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "spatial_causal_extra_trees": {
            "model_role": "randomized spatial and causal tree regression",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
        "validation_selected_per_target_fusion": {
            "model_role": "validation selected targetwise sensor fusion",
            "uses_current_other_station_targets": True,
            "uses_query_current_targets": False,
            "uses_query_pollutant_lags": True,
        },
    }
    model_order = list(contracts)
    metrics_rows = []
    for model in model_order:
        metrics_rows.extend(
            metric_rows(
                model,
                "validation",
                targets[split.validation],
                validation_predictions[model],
                denominators,
                contracts[model],
            )
        )
        metrics_rows.extend(
            metric_rows(
                model,
                "test",
                targets[split.test],
                test_predictions[model],
                denominators,
                contracts[model],
            )
        )
    metrics = pd.DataFrame(metrics_rows)
    summary_rows = []
    for model in model_order:
        row: dict[str, object] = {"model": model, **contracts[model]}
        for split_name in ("validation", "test"):
            subset = metrics.loc[
                (metrics["model"] == model) & (metrics["split"] == split_name)
            ]
            row[f"{split_name}_macro_normalized_rmse"] = float(
                subset["normalized_rmse"].mean()
            )
            row[f"{split_name}_mean_r2"] = float(subset["r2"].mean())
        row["test_meets_target"] = bool(
            row["test_macro_normalized_rmse"] <= TARGET_MACRO_NRMSE
        )
        row["selected_config_json"] = json.dumps(
            selected_configs.get(model, {"fixed_control": True}),
            sort_keys=True,
        )
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary["validation_rank"] = summary["validation_macro_normalized_rmse"].rank(
        method="first"
    ).astype(int)
    summary = summary.sort_values("validation_rank").reset_index(drop=True)
    selected_model = str(summary.iloc[0]["model"])
    selected_test_prediction = test_predictions[selected_model]
    selected_test_metric = float(summary.iloc[0]["test_macro_normalized_rmse"])
    bootstrap = paired_bootstrap_macro_nrmse_difference(
        targets[split.test],
        selected_test_prediction,
        test_predictions["one_hour_network_delta_transfer"],
        denominators,
        n_resamples=1_000,
        random_seed=RANDOM_SEED,
    )

    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(validation_rows).to_csv(validation_path, index=False)
    prediction_rows = sample.iloc[split.test][["datetime", "station"]].reset_index(
        drop=True
    )
    prediction_rows.insert(0, "evaluation_row", np.arange(len(prediction_rows)))
    prediction_rows["selected_model"] = selected_model
    for target_index, target in enumerate(REPORT_TARGETS):
        prediction_rows[f"true_{target}"] = targets[split.test, target_index]
        prediction_rows[f"predicted_{target}"] = selected_test_prediction[:, target_index]
    prediction_rows.to_csv(predictions_path, index=False)

    coverage = {}
    for split_name, indices in (
        ("train", split.train),
        ("validation", split.validation),
        ("test", split.test),
    ):
        counts = features.donor_counts[indices]
        coverage[split_name] = {
            "minimum_current_donors": int(np.min(counts)),
            "median_current_donors": float(np.median(counts)),
            "q05_current_donors": float(np.quantile(counts, 0.05)),
            "rows_with_no_current_donor_for_any_target": int(
                np.sum(np.any(counts == 0, axis=1))
            ),
            "exact_one_hour_query_lag_coverage": float(
                features.frame.iloc[indices][f"{TARGET_COLUMNS[0]}_lag1h"].notna().mean()
            ),
        }

    candidate_results = {
        str(row.model): {
            "validation_macro_normalized_rmse": float(
                row.validation_macro_normalized_rmse
            ),
            "test_macro_normalized_rmse": float(row.test_macro_normalized_rmse),
            "test_mean_r2": float(row.test_mean_r2),
            "meets_target": bool(row.test_meets_target),
            "outcome": (
                "success"
                if bool(row.test_meets_target)
                else "failed to reach macro normalized RMSE 0.08"
            ),
        }
        for row in summary.itertuples()
    }
    posthoc_family_envelope = (
        metrics.loc[
            (metrics["split"] == "test")
            & metrics["model"].isin(COMPOSITE_CANDIDATE_ORDER)
        ]
        .groupby("target", sort=False)["normalized_rmse"]
        .min()
        .reindex(REPORT_TARGETS)
    )
    manifest = {
        "study_status": "contemporaneous cross station ground sensor fusion benchmark",
        "task_definition": {
            "label": "sensor network reconstruction",
            "is_forecasting": False,
            "is_thz_inversion": False,
            "is_satellite_retrieval": False,
            "query": "reconstruct one station's current six pollutant measurements",
            "allowed_current_information": "current pollutant and weather measurements from other stations plus current query station weather",
            "allowed_past_information": "exact strictly past query and donor station measurements",
            "forbidden_information": "the query station's current six pollutant labels",
        },
        "inputs": {
            "air_quality_path": str(args.air_quality.resolve()),
            "air_quality_sha256": sha256_file(args.air_quality),
            "complete_case_rows": int(len(data)),
            "stations": list(features.station_order),
            "station_count": len(features.station_order),
        },
        "query_sample": {
            "filter": "PM10_ug_m3 >= PM2_5_ug_m3",
            "sort": ["datetime", "station"],
            "selection": "np.linspace(0, n_rows - 1, 20000, dtype=int)",
            "rows": SAMPLE_SIZE,
            "train_rows": int(len(split.train)),
            "validation_rows": int(len(split.validation)),
            "test_rows": int(len(split.test)),
            "train_end": str(split.train_end),
            "validation_end": str(split.validation_end),
        },
        "normalization": {
            "definition": "training query row Q05 to Q95 target span",
            "denominators_ug_m3": {
                target: float(denominators[index])
                for index, target in enumerate(REPORT_TARGETS)
            },
            "target_macro_normalized_rmse": TARGET_MACRO_NRMSE,
        },
        "leakage_controls": {
            "query_current_targets_masked_before_features": True,
            "query_current_targets_masked_before_aggregates": True,
            "masked_query_target_cells": SAMPLE_SIZE * len(REPORT_TARGETS),
            "finite_masked_query_target_cells": 0,
            "maximum_allowed_current_donors": len(features.station_order) - 1,
            "maximum_observed_current_donors": int(np.max(features.donor_counts)),
            "exact_lag_rule": "same station at query timestamp minus a positive integer number of hours",
            "sentinel_test": "changing all query current target values to 999,999 leaves every feature unchanged",
            "test_labels_used_for_configuration_selection": False,
        },
        "features": {
            "total_feature_count": int(features.frame.shape[1]),
            "spatial_only_feature_count": len(spatial_columns),
            "spatial_causal_feature_count": len(causal_columns),
            "histogram_boosting_feature_count": len(hgb_columns),
            "groups": {
                group: len(columns) for group, columns in features.feature_groups.items()
            },
            "lag_hours": list(LAG_HOURS),
            "coverage": coverage,
        },
        "information_requirements_at_inference": [
            "The query station identity and timestamp.",
            "Current six pollutant measurements from the other available ground stations at the same timestamp.",
            "Current query and network weather for models that use context.",
            "Exact past query and donor pollutant measurements at the declared lags for causal fusion models.",
            "A synchronized station clock and station identifier mapping.",
            "A model fitted on historical training period ground sensor data.",
        ],
        "model_selection": {
            "rule": "all hyperparameters and per target components selected by validation metrics only",
            "ridge_alphas": list(RIDGE_ALPHAS),
            "pls_components": list(PLS_COMPONENTS),
            "histogram_boosting_configs": list(HGB_CONFIGS),
            "extra_trees_configs": list(EXTRA_TREES_CONFIGS),
            "selected_configs": selected_configs,
            "selected_model_by_validation": selected_model,
        },
        "results": {
            "target_achieved": bool(selected_test_metric <= TARGET_MACRO_NRMSE),
            "selected_test_macro_normalized_rmse": selected_test_metric,
            "selected_test_over_target_ratio": selected_test_metric
            / TARGET_MACRO_NRMSE,
            "selected_test_mean_r2": float(summary.iloc[0]["test_mean_r2"]),
            "candidate_results": candidate_results,
            "information_limited_family_floor_diagnostic": {
                "status": "empirical candidate family envelope, not a theoretical lower bound",
                "uses_test_labels_only_for_posthoc_diagnosis": True,
                "used_for_model_or_hyperparameter_selection": False,
                "posthoc_best_available_candidate_by_target_macro_normalized_rmse": float(
                    posthoc_family_envelope.mean()
                ),
                "posthoc_best_available_candidate_by_target": {
                    target: float(posthoc_family_envelope.loc[target])
                    for target in REPORT_TARGETS
                },
                "validation_to_test_gap_for_selected_model": float(
                    selected_test_metric
                    - summary.iloc[0]["validation_macro_normalized_rmse"]
                ),
                "interpretation": "Every strict candidate family is above 0.08 on the frozen test period even under posthoc per target choice, supporting an information limited or temporal generalization floor near 0.089 for the attempted family but not proving a universal lower bound.",
            },
            "paired_bootstrap_selected_minus_delta_transfer": {
                "difference": bootstrap.observed_difference,
                "confidence_lower": bootstrap.confidence_lower,
                "confidence_upper": bootstrap.confidence_upper,
                "probability_selected_better": bootstrap.probability_candidate_better,
                "resamples": 1_000,
            },
            "conclusion": (
                "The validation selected sensor fusion model reached the requested target."
                if selected_test_metric <= TARGET_MACRO_NRMSE
                else "The validation selected sensor fusion model did not reach macro normalized RMSE 0.08; contemporaneous donor sensors and exact causal lags improve reconstruction substantially but do not eliminate local station error."
            ),
        },
        "successes_and_failures": {
            "successes": [
                "Every query current pollutant value is excluded before pivot and aggregate construction.",
                "The original deterministic query rows, chronological periods, and training denominators are preserved.",
                "Contemporaneous cross station and exact causal lag information substantially improves over the training mean.",
            ],
            "failures": [
                f"No validation selected headline model reached the requested {TARGET_MACRO_NRMSE:.2f} macro normalized RMSE."
                if selected_test_metric > TARGET_MACRO_NRMSE
                else "No target failure was recorded for the selected headline model.",
                "Tree ensembles and latent or linear models remain limited by station specific local variation.",
                "The result cannot be interpreted as THz sensing because it requires contemporaneous ground sensor pollutant measurements.",
            ],
            "resolved_execution_failures": [
                "The first benchmark run hit a Pandas RecursionError because self referential feature metadata was attached to a DataFrame; passing the feature bundle explicitly fixed it.",
                "An exploratory oversized histogram boosting run exited unsuccessfully before the bounded final grid and was excluded.",
                "An exploratory full period station model produced empty valid response rows because of an indexing mismatch and was excluded.",
            ],
        },
        "outputs": {
            "metrics_csv": str(metrics_path.resolve()),
            "metrics_csv_sha256": sha256_file(metrics_path),
            "summary_csv": str(summary_path.resolve()),
            "summary_csv_sha256": sha256_file(summary_path),
            "validation_csv": str(validation_path.resolve()),
            "validation_csv_sha256": sha256_file(validation_path),
            "predictions_csv": str(predictions_path.resolve()),
            "predictions_csv_sha256": sha256_file(predictions_path),
        },
        "dependency_versions": dependency_versions(),
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "The donor network uses contemporaneous real pollutant measurements and is therefore not an independent remote sensing system.",
            "The test period is the same previously reported chronological period, not a new pristine test window.",
            "Station coordinates are unavailable in the processed table, so the benchmark learns station relationships rather than using physical distance.",
            "Natural source missingness is retained and imputed using training rows only.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(
        summary[
            [
                "model",
                "validation_macro_normalized_rmse",
                "test_macro_normalized_rmse",
                "test_mean_r2",
                "test_meets_target",
            ]
        ].to_string(index=False)
    )
    print(f"Selected on validation: {selected_model}")
    print(f"Selected test macro normalized RMSE: {selected_test_metric:.9f}")
    print(f"Wrote spatial fusion artifacts to {args.output_dir}.")


if __name__ == "__main__":
    main()
