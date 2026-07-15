"""Benchmark contemporaneous single channel ground sensor repair.

For target channel j, the query station's current j value is masked while its
other five current pollutant channels are allowed. This diagnostic is not the
strict all-six-masked sensor network reconstruction task, forecasting, or THz
inversion.
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
from sklearn.ensemble import HistGradientBoostingRegressor
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
from thz_isac.single_channel_repair import (  # noqa: E402
    assert_repaired_current_target_excluded,
    build_single_channel_repair_features,
    repair_frame_for_target,
)
from thz_isac.spatial_fusion import (  # noqa: E402
    assert_query_current_targets_excluded,
    build_spatial_fusion_features,
    compose_per_target_predictions,
    feature_columns_for_groups,
    lag_delta_transfer_prediction,
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
HGB_CONFIGS = (
    {
        "max_iter": 160,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 30,
        "l2_regularization": 10.0,
    },
    {
        "max_iter": 220,
        "max_leaf_nodes": 31,
        "min_samples_leaf": 30,
        "l2_regularization": 20.0,
    },
)
STRICT_GROUPS = (
    "spatial_current_pivot",
    "spatial_current_aggregate",
    "query_causal_lag",
    "spatial_change_pivot",
    "spatial_change_aggregate",
    "query_weather",
    "network_weather",
    "calendar",
    "station_identity",
)
CANDIDATE_ORDER = (
    "strict_one_hour_network_delta_reference",
    "single_channel_global_ridge",
    "single_channel_station_delta_ridge",
    "single_channel_histogram_boosting",
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


def target_nrmse(
    truth: np.ndarray,
    prediction: np.ndarray,
    denominator: float,
) -> float:
    """Return one target normalized RMSE."""
    return float(np.sqrt(np.mean((truth - prediction) ** 2)) / denominator)


def prepare_target_design(
    strict_frame: pd.DataFrame,
    strict_columns: list[str],
    repair_frame: pd.DataFrame,
    split,
) -> tuple[
    tuple[np.ndarray, np.ndarray, np.ndarray],
    tuple[np.ndarray, np.ndarray, np.ndarray],
]:
    """Create raw and training-only imputed and scaled target designs."""
    design = pd.concat(
        [
            strict_frame[strict_columns].reset_index(drop=True),
            repair_frame.reset_index(drop=True),
        ],
        axis=1,
    )
    raw = (
        design.iloc[split.train].to_numpy(float),
        design.iloc[split.validation].to_numpy(float),
        design.iloc[split.test].to_numpy(float),
    )
    imputer = SimpleImputer(
        strategy="median",
        add_indicator=True,
        keep_empty_features=True,
    )
    imputed = (
        imputer.fit_transform(raw[0]),
        imputer.transform(raw[1]),
        imputer.transform(raw[2]),
    )
    scaler = StandardScaler()
    scaled = (
        scaler.fit_transform(imputed[0]),
        scaler.transform(imputed[1]),
        scaler.transform(imputed[2]),
    )
    return raw, scaled


def fit_global_ridge(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    target: np.ndarray,
    split,
    target_mean: float,
    denominator: float,
    target_name: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a target Ridge alpha using validation labels only."""
    scaled_target = (target - target_mean) / denominator
    best_score = np.inf
    best_model: Ridge | None = None
    best_validation: np.ndarray | None = None
    best_alpha = np.nan
    rows = []
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(blocks[0], scaled_target[split.train])
        validation_prediction = model.predict(blocks[1]) * denominator + target_mean
        score = target_nrmse(
            target[split.validation], validation_prediction, denominator
        )
        rows.append(
            {
                "model": "single_channel_global_ridge",
                "target": target_name,
                "candidate_json": json.dumps({"alpha": alpha}, sort_keys=True),
                "validation_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_model = model
            best_validation = validation_prediction
            best_alpha = alpha
    if best_model is None or best_validation is None:
        raise RuntimeError("Global Ridge validation selection failed")
    test_prediction = best_model.predict(blocks[2]) * denominator + target_mean
    return best_validation, test_prediction, {"alpha": best_alpha}, rows


def fit_target_hgb(
    blocks: tuple[np.ndarray, np.ndarray, np.ndarray],
    target: np.ndarray,
    split,
    target_mean: float,
    denominator: float,
    target_name: str,
    target_index: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a target histogram boosting configuration on validation only."""
    scaled_target = (target - target_mean) / denominator
    best_score = np.inf
    best_model: HistGradientBoostingRegressor | None = None
    best_validation: np.ndarray | None = None
    best_config: dict[str, object] | None = None
    rows = []
    for config_index, config in enumerate(HGB_CONFIGS):
        model = HistGradientBoostingRegressor(
            **config,
            learning_rate=0.05,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20,
            random_state=RANDOM_SEED + 100 * target_index + config_index,
        )
        model.fit(blocks[0], scaled_target[split.train])
        validation_prediction = model.predict(blocks[1]) * denominator + target_mean
        score = target_nrmse(
            target[split.validation], validation_prediction, denominator
        )
        candidate = {
            **config,
            "learning_rate": 0.05,
            "early_stopping": True,
            "fitted_iterations": int(model.n_iter_),
        }
        rows.append(
            {
                "model": "single_channel_histogram_boosting",
                "target": target_name,
                "candidate_json": json.dumps(candidate, sort_keys=True),
                "validation_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_model = model
            best_validation = validation_prediction
            best_config = candidate
    if best_model is None or best_validation is None or best_config is None:
        raise RuntimeError("Histogram boosting validation selection failed")
    test_prediction = best_model.predict(blocks[2]) * denominator + target_mean
    return best_validation, test_prediction, best_config, rows


def fit_station_delta_ridge(
    strict_features,
    repair_frame: pd.DataFrame,
    sample: pd.DataFrame,
    target: np.ndarray,
    target_column: str,
    split,
    denominator: float,
    fallback_validation: np.ndarray,
    fallback_test: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Fit station specific Ridge models for the repaired target change."""
    frame = pd.concat(
        [strict_features.frame.reset_index(drop=True), repair_frame.reset_index(drop=True)],
        axis=1,
    )
    validation_prediction = fallback_validation.copy()
    test_prediction = fallback_test.copy()
    validation_sample = sample.iloc[split.validation].reset_index(drop=True)
    test_sample = sample.iloc[split.test].reset_index(drop=True)
    context_columns = feature_columns_for_groups(
        strict_features,
        ("query_weather", "network_weather", "calendar"),
    )
    lag_columns = [
        f"{column}_lag{lag}h"
        for lag in (1, 2, 3)
        for column in TARGET_COLUMNS
    ]
    target_columns = [
        column
        for column in strict_features.frame.columns
        if column.startswith(f"current_other__{target_column}__")
        or column.startswith(f"change_other__{target_column}__lag1h__")
    ]
    model_columns = list(
        dict.fromkeys(
            [
                *target_columns,
                *lag_columns,
                *context_columns,
                *repair_frame.columns,
            ]
        )
    )
    query_lag = frame[f"{target_column}_lag1h"].to_numpy(float)
    response = target - query_lag
    selected_alphas = {}
    rows = []

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
        valid_train = train_indices[np.isfinite(response[train_indices])]
        if len(valid_train) < 100:
            raise RuntimeError(f"Insufficient valid station training rows: {station}")

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
        best_validation: np.ndarray | None = None
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
                fallback_validation[validation_positions],
            )
            score = target_nrmse(
                target[validation_indices], station_validation, denominator
            )
            rows.append(
                {
                    "model": "single_channel_station_delta_ridge",
                    "target": target_column,
                    "candidate_json": json.dumps(
                        {"station": station, "alpha": alpha}, sort_keys=True
                    ),
                    "validation_normalized_rmse": score,
                }
            )
            if score < best_score:
                best_score = score
                best_model = model
                best_validation = station_validation
                best_alpha = alpha
        if best_model is None or best_validation is None:
            raise RuntimeError("Station delta Ridge validation selection failed")
        station_test = query_lag[test_indices] + best_model.predict(test_x)
        station_test = np.where(
            np.isfinite(station_test),
            station_test,
            fallback_test[test_positions],
        )
        validation_prediction[validation_positions] = best_validation
        test_prediction[test_positions] = station_test
        selected_alphas[station] = float(best_alpha)
    return validation_prediction, test_prediction, selected_alphas, rows


def metric_rows(
    model: str,
    split_name: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> list[dict[str, object]]:
    """Return auditable target metrics for one candidate and split."""
    metrics = multi_target_regression_metrics(truth, prediction, denominators)
    return [
        {
            "model": model,
            "split": split_name,
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
    """Run the single channel sensor repair diagnostic."""
    args = parse_args()
    started = time.perf_counter()
    if not args.air_quality.exists():
        raise FileNotFoundError(f"Required input does not exist: {args.air_quality}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = args.output_dir / "single_channel_repair_metrics.csv"
    summary_path = args.output_dir / "single_channel_repair_summary.csv"
    validation_path = args.output_dir / "single_channel_repair_validation.csv"
    predictions_path = args.output_dir / "single_channel_repair_predictions.csv"
    manifest_path = args.output_dir / "single_channel_repair_manifest.json"

    print("Loading the real Beijing ground station dataset.")
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    if data.duplicated(["station", "datetime"]).any():
        raise ValueError("Air quality source contains duplicate station timestamp keys")
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

    print("Building strict donor features and target specific repair covariates.")
    strict_features = build_spatial_fusion_features(
        data,
        sample,
        TARGET_COLUMNS,
        WEATHER_COLUMNS,
        LAG_HOURS,
    )
    assert_query_current_targets_excluded(strict_features)
    repair_features = build_single_channel_repair_features(sample, TARGET_COLUMNS)
    assert_repaired_current_target_excluded(repair_features)
    strict_columns = feature_columns_for_groups(strict_features, STRICT_GROUPS)
    hgb_columns = [
        column
        for column in strict_columns
        if "lag6h" not in column and "lag24h" not in column
    ]

    strict_delta = lag_delta_transfer_prediction(strict_features, 1, target_mean)
    validation_predictions: dict[str, np.ndarray] = {
        "strict_one_hour_network_delta_reference": strict_delta[split.validation]
    }
    test_predictions: dict[str, np.ndarray] = {
        "strict_one_hour_network_delta_reference": strict_delta[split.test]
    }
    for name in CANDIDATE_ORDER[1:]:
        validation_predictions[name] = np.empty(
            (len(split.validation), len(TARGET_COLUMNS))
        )
        test_predictions[name] = np.empty((len(split.test), len(TARGET_COLUMNS)))

    selected_configs: dict[str, dict[str, object]] = {
        name: {} for name in CANDIDATE_ORDER[1:]
    }
    validation_rows: list[dict[str, object]] = []
    for target_index, (report_target, target_column) in enumerate(
        zip(REPORT_TARGETS, TARGET_COLUMNS, strict=True)
    ):
        print(f"Selecting repair models for {report_target} on validation only.")
        repair_frame = repair_frame_for_target(repair_features, target_column)
        raw, scaled = prepare_target_design(
            strict_features.frame,
            strict_columns,
            repair_frame,
            split,
        )
        ridge_validation, ridge_test, ridge_config, rows = fit_global_ridge(
            scaled,
            targets[:, target_index],
            split,
            target_mean[target_index],
            denominators[target_index],
            report_target,
        )
        validation_predictions["single_channel_global_ridge"][:, target_index] = (
            ridge_validation
        )
        test_predictions["single_channel_global_ridge"][:, target_index] = ridge_test
        selected_configs["single_channel_global_ridge"][report_target] = ridge_config
        validation_rows.extend(rows)

        station_validation, station_test, station_config, rows = (
            fit_station_delta_ridge(
                strict_features,
                repair_frame,
                sample,
                targets[:, target_index],
                target_column,
                split,
                denominators[target_index],
                strict_delta[split.validation, target_index],
                strict_delta[split.test, target_index],
            )
        )
        validation_predictions["single_channel_station_delta_ridge"][
            :, target_index
        ] = station_validation
        test_predictions["single_channel_station_delta_ridge"][:, target_index] = (
            station_test
        )
        selected_configs["single_channel_station_delta_ridge"][report_target] = (
            station_config
        )
        validation_rows.extend(rows)

        raw_hgb = (
            np.column_stack(
                [
                    strict_features.frame.iloc[split.train][hgb_columns].to_numpy(
                        float
                    ),
                    raw[0][:, len(strict_columns) :],
                ]
            ),
            np.column_stack(
                [
                    strict_features.frame.iloc[split.validation][
                        hgb_columns
                    ].to_numpy(float),
                    raw[1][:, len(strict_columns) :],
                ]
            ),
            np.column_stack(
                [
                    strict_features.frame.iloc[split.test][hgb_columns].to_numpy(
                        float
                    ),
                    raw[2][:, len(strict_columns) :],
                ]
            ),
        )
        hgb_validation, hgb_test, hgb_config, rows = fit_target_hgb(
            raw_hgb,
            targets[:, target_index],
            split,
            target_mean[target_index],
            denominators[target_index],
            report_target,
            target_index,
        )
        validation_predictions["single_channel_histogram_boosting"][
            :, target_index
        ] = hgb_validation
        test_predictions["single_channel_histogram_boosting"][:, target_index] = (
            hgb_test
        )
        selected_configs["single_channel_histogram_boosting"][report_target] = (
            hgb_config
        )
        validation_rows.extend(rows)

    selected_components = select_per_target_by_validation(
        targets[split.validation],
        validation_predictions,
        denominators,
        CANDIDATE_ORDER,
    )
    selected_name = "validation_selected_single_channel_repair"
    validation_predictions[selected_name] = compose_per_target_predictions(
        selected_components, validation_predictions
    )
    test_predictions[selected_name] = compose_per_target_predictions(
        selected_components, test_predictions
    )
    selected_configs[selected_name] = {
        report_target: selected_components[target_index]
        for target_index, report_target in enumerate(REPORT_TARGETS)
    }

    model_order = (*CANDIDATE_ORDER, selected_name)
    all_metrics = []
    for model in model_order:
        all_metrics.extend(
            metric_rows(
                model,
                "validation",
                targets[split.validation],
                validation_predictions[model],
                denominators,
            )
        )
        all_metrics.extend(
            metric_rows(
                model,
                "test",
                targets[split.test],
                test_predictions[model],
                denominators,
            )
        )
    metrics = pd.DataFrame(all_metrics)
    summary_rows = []
    for model in model_order:
        row: dict[str, object] = {"model": model}
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
            selected_configs.get(model, {"fixed_reference": True}), sort_keys=True
        )
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    summary["validation_rank"] = summary[
        "validation_macro_normalized_rmse"
    ].rank(method="first").astype(int)
    summary = summary.sort_values("validation_rank").reset_index(drop=True)
    selected_test = test_predictions[selected_name]
    selected_test_metric = float(
        summary.loc[
            summary["model"] == selected_name, "test_macro_normalized_rmse"
        ].iloc[0]
    )
    bootstrap = paired_bootstrap_macro_nrmse_difference(
        targets[split.test],
        selected_test,
        test_predictions["strict_one_hour_network_delta_reference"],
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
    for target_index, target in enumerate(REPORT_TARGETS):
        prediction_rows[f"true_{target}"] = targets[split.test, target_index]
        prediction_rows[f"predicted_{target}"] = selected_test[:, target_index]
        prediction_rows[f"selected_component_{target}"] = selected_components[
            target_index
        ]
    prediction_rows.to_csv(predictions_path, index=False)

    strict_summary_path = args.output_dir / "spatial_fusion_summary.csv"
    strict_reference = None
    if strict_summary_path.exists():
        strict_summary = pd.read_csv(strict_summary_path)
        strict_row = strict_summary.loc[
            strict_summary["model"] == "validation_selected_per_target_fusion"
        ]
        if len(strict_row) == 1:
            strict_reference = {
                "validation_macro_normalized_rmse": float(
                    strict_row.iloc[0]["validation_macro_normalized_rmse"]
                ),
                "test_macro_normalized_rmse": float(
                    strict_row.iloc[0]["test_macro_normalized_rmse"]
                ),
                "summary_sha256": sha256_file(strict_summary_path),
            }

    candidate_results = {
        str(row.model): {
            "validation_macro_normalized_rmse": float(
                row.validation_macro_normalized_rmse
            ),
            "test_macro_normalized_rmse": float(row.test_macro_normalized_rmse),
            "test_mean_r2": float(row.test_mean_r2),
            "meets_target": bool(row.test_meets_target),
        }
        for row in summary.itertuples()
    }
    manifest = {
        "study_status": "single channel contemporaneous ground sensor repair benchmark",
        "task_definition": {
            "label": "single channel sensor repair",
            "strict_all_six_masked_reconstruction": False,
            "is_forecasting": False,
            "is_thz_inversion": False,
            "query": "repair one current pollutant channel at one station",
            "allowed_current_information": "the other five current pollutant channels at the query station, current donor station pollutants, and current weather",
            "forbidden_information": "the current query station value of the channel being repaired",
        },
        "strict_primary_reference": strict_reference,
        "inputs": {
            "air_quality_path": str(args.air_quality.resolve()),
            "air_quality_sha256": sha256_file(args.air_quality),
            "complete_case_rows": int(len(data)),
            "stations": list(strict_features.station_order),
        },
        "query_sample": {
            "filter": "PM10_ug_m3 >= PM2_5_ug_m3",
            "selection": "np.linspace(0, n_rows - 1, 20000, dtype=int)",
            "rows": SAMPLE_SIZE,
            "train_rows": int(len(split.train)),
            "validation_rows": int(len(split.validation)),
            "test_rows": int(len(split.test)),
            "train_end": str(split.train_end),
            "validation_end": str(split.validation_end),
        },
        "normalization": {
            "definition": "strict benchmark training query row Q05 to Q95 target span",
            "denominators_ug_m3": {
                target: float(denominators[index])
                for index, target in enumerate(REPORT_TARGETS)
            },
            "target_macro_normalized_rmse": TARGET_MACRO_NRMSE,
        },
        "leakage_controls": {
            "current_repaired_target_diagonal_is_all_missing": bool(
                np.isnan(
                    repair_features.current_query_values[
                        :,
                        np.arange(len(TARGET_COLUMNS)),
                        np.arange(len(TARGET_COLUMNS)),
                    ]
                ).all()
            ),
            "masked_current_repaired_target_cells": SAMPLE_SIZE
            * len(TARGET_COLUMNS),
            "current_other_five_query_channels_allowed": True,
            "strict_donor_features_mask_all_six_query_targets": True,
            "sentinel_test": "changing repaired target j to 999,999 leaves the target j repair design unchanged",
            "test_labels_used_for_configuration_selection": False,
        },
        "information_requirements_at_inference": [
            "The query station identity, timestamp, and identity of the failed channel.",
            "The other five current pollutant measurements from the query station.",
            "Current pollutant measurements from available donor stations at the same timestamp.",
            "Current weather and exact past pollutant measurements at the declared lags.",
            "A synchronized station clock and a model fitted on the historical training period.",
        ],
        "model_selection": {
            "rule": "all hyperparameters and target components selected using validation metrics only",
            "candidate_order": list(CANDIDATE_ORDER),
            "selected_component_by_target": {
                target: selected_components[index]
                for index, target in enumerate(REPORT_TARGETS)
            },
            "selected_configs": selected_configs,
        },
        "results": {
            "target_achieved": bool(selected_test_metric <= TARGET_MACRO_NRMSE),
            "selected_test_macro_normalized_rmse": selected_test_metric,
            "candidate_results": candidate_results,
            "paired_bootstrap_selected_minus_strict_delta_reference": {
                "difference": bootstrap.observed_difference,
                "confidence_lower": bootstrap.confidence_lower,
                "confidence_upper": bootstrap.confidence_upper,
                "probability_selected_better": bootstrap.probability_candidate_better,
                "resamples": 1_000,
            },
            "interpretation": "Any score improvement applies only to single channel repair because it requires the other five current query station pollutant measurements.",
        },
        "successes_and_failures": {
            "successes": [
                "The repaired current target is excluded from its target specific feature design.",
                "The deterministic rows, chronological periods, and strict training denominators are unchanged.",
            ],
            "failures": [
                "This diagnostic cannot support a strict all-six-masked reconstruction claim.",
                "This diagnostic cannot support a THz inversion claim because it consumes current ground sensor pollutant channels.",
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
            "The evaluation population retains the original PM10 greater than or equal to PM2.5 filter.",
            "The test period is a previously used chronological period, not a new pristine test window.",
            "Natural source missingness is retained and Ridge imputation is fitted on training rows only.",
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
    print(f"Selected component by target: {selected_configs[selected_name]}")
    print(f"Selected test macro normalized RMSE: {selected_test_metric:.9f}")
    print(f"Wrote single channel repair artifacts to {args.output_dir}.")


if __name__ == "__main__":
    main()
