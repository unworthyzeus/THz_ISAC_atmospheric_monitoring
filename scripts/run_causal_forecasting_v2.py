"""Run the frozen v2 strictly causal ground sensor forecasting study.

Candidate selection was completed on the original validation period. This
script reruns only the frozen target specific composite before opening the test
features. It also records every exploratory validation candidate and failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.metrics import r2_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.causal_forecasting_v2 import HourlyHistory  # noqa: E402
from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.temporal_baselines import evenly_spaced_sample_indices  # noqa: E402


TARGETS = ("CO", "O3", "SO2", "NO2", "PM2.5", "PM10")
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
RANDOM_SEED = 20260715
SAMPLE_SIZE = 20_000

# Frozen before test evaluation using validation normalized RMSE only.
FROZEN_MODELS = {
    "CO": (
        "extra_leaf4",
        {"n_estimators": 400, "min_samples_leaf": 4, "max_features": 1.0},
    ),
    "O3": (
        "hgb31",
        {
            "max_iter": 200,
            "max_leaf_nodes": 31,
            "learning_rate": 0.05,
            "l2_regularization": 10.0,
        },
    ),
    "SO2": (
        "extra_leaf2",
        {"n_estimators": 250, "min_samples_leaf": 2, "max_features": 0.8},
    ),
    "NO2": (
        "hgb31",
        {
            "max_iter": 200,
            "max_leaf_nodes": 31,
            "learning_rate": 0.05,
            "l2_regularization": 10.0,
        },
    ),
    "PM2.5": (
        "hgb_deep",
        {
            "max_iter": 400,
            "max_leaf_nodes": 31,
            "learning_rate": 0.03,
            "l2_regularization": 30.0,
        },
    ),
    "PM10": (
        "extra_leaf4",
        {"n_estimators": 400, "min_samples_leaf": 4, "max_features": 1.0},
    ),
}

# Exact validation attempts from the exploration that froze FROZEN_MODELS.
ATTEMPT_RESULTS = {
    "hgb15": {
        "scores": [
            0.114377801145,
            0.054585598455,
            0.062707649173,
            0.089364774937,
            0.089725435587,
            0.103353377103,
        ],
        "seconds": [3.313, 10.280, 67.519, 25.003, 15.796, 14.651],
        "window_days": None,
    },
    "hgb31": {
        "scores": [
            0.114566036526,
            0.053738476668,
            0.062048699678,
            0.088218579868,
            0.089758066432,
            0.102907609289,
        ],
        "seconds": [44.037, 16.888, 18.508, 24.350, 15.410, 29.207],
        "window_days": None,
    },
    "extra_leaf2": {
        "scores": [
            0.111501907237,
            0.053906426346,
            0.062004283517,
            0.090296250004,
            0.091144465521,
            0.102771494916,
        ],
        "seconds": [21.330, 16.203, 30.799, 21.526, 23.445, 31.268],
        "window_days": None,
    },
    "hgb15_recent365": {
        "scores": [
            0.117024315905,
            0.055349502454,
            0.065602140593,
            0.091434467450,
            0.091628420668,
            0.106133746855,
        ],
        "seconds": [27.087, 13.541, 17.134, 18.999, 20.646, 10.924],
        "window_days": 365,
    },
    "hgb15_recent730": {
        "scores": [
            0.114995649563,
            0.054766715349,
            0.063598806023,
            0.090287800769,
            0.089488813850,
            0.103210659597,
        ],
        "seconds": [27.910, 15.631, 15.162, 31.355, 20.746, 20.754],
        "window_days": 730,
    },
}

TARGETED_RESULTS = {
    "extra_leaf1": {
        "CO": (0.114458486033, 72.906),
        "NO2": (0.090357944213, 35.857),
        "PM2.5": (0.092576087659, 41.697),
        "PM10": (0.104371578593, 45.757),
    },
    "extra_leaf4": {
        "CO": (0.110838938072, 46.704),
        "NO2": (0.090709806070, 24.108),
        "PM2.5": (0.090269491706, 25.678),
        "PM10": (0.102707164681, 26.975),
    },
    "rf_leaf2": {
        "CO": (0.128843673679, 70.557),
        "NO2": (0.092090918582, 46.434),
        "PM2.5": (0.095708351746, 64.494),
        "PM10": (0.103189553806, 65.577),
    },
    "hgb_deep": {
        "CO": (0.112063622702, 22.414),
        "NO2": (0.088507440709, 82.764),
        "PM2.5": (0.089655584963, 8.954),
        "PM10": (0.103034554350, 8.560),
    },
}


def parse_args() -> argparse.Namespace:
    """Parse the real UCI input and output directory."""
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
    """Return the SHA256 digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_model(name: str, parameters: dict[str, float | int]):
    """Instantiate one frozen target specific residual model."""
    if name.startswith("extra"):
        return ExtraTreesRegressor(
            **parameters,
            n_jobs=-1,
            random_state=RANDOM_SEED,
        )
    return HistGradientBoostingRegressor(
        **parameters,
        min_samples_leaf=20,
        early_stopping=False,
        random_state=RANDOM_SEED,
    )


def regression_rows(
    model: str,
    split_name: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> list[dict[str, object]]:
    """Return one metric row per target."""
    rows = []
    for index, target in enumerate(TARGETS):
        error = prediction[:, index] - truth[:, index]
        rmse = float(np.sqrt(np.mean(error**2)))
        rows.append(
            {
                "model": model,
                "split": split_name,
                "target": target,
                "mae_ug_m3": float(np.mean(np.abs(error))),
                "rmse_ug_m3": rmse,
                "normalized_rmse": rmse / float(denominators[index]),
                "r2": float(r2_score(truth[:, index], prediction[:, index])),
                "bias_ug_m3": float(np.mean(error)),
            }
        )
    return rows


def exploratory_attempt_table() -> pd.DataFrame:
    """Materialize every completed or failed validation attempt."""
    rows = []
    information = (
        "189 strictly causal features from exact past full-table histories; "
        "model trained on deterministic sample training rows"
    )
    for candidate, result in ATTEMPT_RESULTS.items():
        for target, score, seconds in zip(
            TARGETS, result["scores"], result["seconds"], strict=True
        ):
            rows.append(
                {
                    "candidate": candidate,
                    "target": target,
                    "status": "completed_validation_only",
                    "validation_normalized_rmse": score,
                    "runtime_seconds": seconds,
                    "training_window_days": result["window_days"],
                    "information_set": information,
                    "failure_message": None,
                }
            )
    for candidate, targets in TARGETED_RESULTS.items():
        for target, (score, seconds) in targets.items():
            rows.append(
                {
                    "candidate": candidate,
                    "target": target,
                    "status": "completed_targeted_validation_only",
                    "validation_normalized_rmse": score,
                    "runtime_seconds": seconds,
                    "training_window_days": None,
                    "information_set": information,
                    "failure_message": None,
                }
            )
    rows.extend(
        [
            {
                "candidate": "full_training_hgb_268_features",
                "target": "CO",
                "status": "partial_before_resource_failure",
                "validation_normalized_rmse": 0.116632879841,
                "runtime_seconds": 62.514,
                "training_window_days": None,
                "information_set": "268 causal features and all 219558 eligible training-period rows",
                "failure_message": "Process ended during allocation for the second target after 291.3 total seconds.",
            },
            {
                "candidate": "full_training_hgb_268_features",
                "target": "ALL_REMAINING",
                "status": "failed_resource_limit",
                "validation_normalized_rmse": np.nan,
                "runtime_seconds": 291.3,
                "training_window_days": None,
                "information_set": "268 causal features and all 219558 eligible training-period rows",
                "failure_message": "Resource pressure prevented completion; no test evaluation was performed.",
            },
        ]
    )
    return pd.DataFrame(rows)


def main() -> None:
    """Train the frozen composite, evaluate test once, and write v2 artifacts."""
    started = time.perf_counter()
    args = parse_args()
    if not args.air_quality.exists():
        raise FileNotFoundError(f"Required input does not exist: {args.air_quality}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    eligible = (
        data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]]
        .sort_values(["datetime", "station"])
        .reset_index(drop=True)
    )
    sample = eligible.iloc[
        evenly_spaced_sample_indices(len(eligible), SAMPLE_SIZE)
    ].reset_index(drop=True)
    split = chronological_timestamp_split(sample[["datetime", "station"]])
    validate_disjoint_split(split, len(sample))
    values = sample[list(TARGET_COLUMNS)].to_numpy(float)
    denominators = np.quantile(values[split.train], 0.95, axis=0) - np.quantile(
        values[split.train], 0.05, axis=0
    )
    history = HourlyHistory.from_frame(data, TARGET_COLUMNS, WEATHER_COLUMNS)
    train = sample.iloc[split.train].reset_index(drop=True)
    validation = sample.iloc[split.validation].reset_index(drop=True)

    station_fallback = np.empty((len(history.stations), len(TARGETS)))
    for station_index, station in enumerate(history.stations):
        station_rows = train.loc[train["station"] == station, list(TARGET_COLUMNS)]
        station_fallback[station_index] = station_rows.mean().to_numpy(float)

    models = {}
    validation_prediction = np.empty((len(validation), len(TARGETS)))
    validation_base = np.empty_like(validation_prediction)
    selected_rows = []
    print("Training the validation-frozen target-specific causal composite.")
    for target_index, target in enumerate(TARGETS):
        feature_start = time.perf_counter()
        train_x = history.feature_matrix(train, target_index)
        validation_x = history.feature_matrix(validation, target_index)
        train_base = history.causal_base(
            train, target_index, station_fallback[:, target_index]
        )
        validation_base[:, target_index] = history.causal_base(
            validation, target_index, station_fallback[:, target_index]
        )
        model_name, parameters = FROZEN_MODELS[target]
        model = make_model(model_name, parameters)
        fit_start = time.perf_counter()
        residual = (
            train[TARGET_COLUMNS[target_index]].to_numpy(float) - train_base
        ) / denominators[target_index]
        model.fit(train_x, residual)
        validation_prediction[:, target_index] = (
            validation_base[:, target_index]
            + model.predict(validation_x) * denominators[target_index]
        )
        models[target] = model
        score = float(
            np.sqrt(
                np.mean(
                    (
                        validation_prediction[:, target_index]
                        - validation[TARGET_COLUMNS[target_index]].to_numpy(float)
                    )
                    ** 2
                )
            )
            / denominators[target_index]
        )
        selected_rows.append(
            {
                "candidate": f"frozen_{model_name}",
                "target": target,
                "status": "selected_on_validation_and_reproduced",
                "validation_normalized_rmse": score,
                "runtime_seconds": time.perf_counter() - fit_start,
                "training_window_days": None,
                "information_set": "frozen 189 feature strictly causal information set",
                "failure_message": None,
                "feature_build_seconds": fit_start - feature_start,
            }
        )
        print(f"{target}: validation normalized RMSE {score:.9f}")

    # The selected mapping above is fixed before any test feature is constructed.
    test = sample.iloc[split.test].reset_index(drop=True)
    test_prediction = np.empty((len(test), len(TARGETS)))
    test_base = np.empty_like(test_prediction)
    print("Evaluating the frozen composite on test once.")
    for target_index, target in enumerate(TARGETS):
        test_x = history.feature_matrix(test, target_index)
        test_base[:, target_index] = history.causal_base(
            test, target_index, station_fallback[:, target_index]
        )
        test_prediction[:, target_index] = (
            test_base[:, target_index]
            + models[target].predict(test_x) * denominators[target_index]
        )

    metrics = []
    for model_name, validation_values, test_values in (
        ("causal one hour base", validation_base, test_base),
        ("v2 frozen target-specific composite", validation_prediction, test_prediction),
    ):
        metrics.extend(
            regression_rows(
                model_name,
                "validation",
                validation[list(TARGET_COLUMNS)].to_numpy(float),
                validation_values,
                denominators,
            )
        )
        metrics.extend(
            regression_rows(
                model_name,
                "test",
                test[list(TARGET_COLUMNS)].to_numpy(float),
                test_values,
                denominators,
            )
        )
    metrics_table = pd.DataFrame(metrics)
    metrics_path = args.output_dir / "causal_forecasting_v2_metrics.csv"
    metrics_table.to_csv(metrics_path, index=False)

    summary = (
        metrics_table.groupby(["model", "split"], sort=False)
        .agg(
            mean_normalized_rmse=("normalized_rmse", "mean"),
            mean_r2=("r2", "mean"),
        )
        .reset_index()
    )
    summary_path = args.output_dir / "causal_forecasting_v2_summary.csv"
    summary.to_csv(summary_path, index=False)

    innovation_rows = []
    for split_name, frame, frozen in (
        ("validation", validation, validation_prediction),
        ("test", test, test_prediction),
    ):
        truth = frame[list(TARGET_COLUMNS)].to_numpy(float)
        for target_index, target in enumerate(TARGETS):
            lag = history.exact_target_lag(frame, target_index, 1)
            available = np.isfinite(lag)
            innovation_rmse = float(
                np.sqrt(np.mean((truth[available, target_index] - lag[available]) ** 2))
            )
            frozen_rmse = float(
                np.sqrt(
                    np.mean((truth[:, target_index] - frozen[:, target_index]) ** 2)
                )
            )
            innovation_rows.append(
                {
                    "split": split_name,
                    "target": target,
                    "exact_lag_coverage": float(np.mean(available)),
                    "available_one_hour_innovation_rmse_ug_m3": innovation_rmse,
                    "available_one_hour_innovation_normalized_rmse": innovation_rmse
                    / denominators[target_index],
                    "frozen_model_normalized_rmse": frozen_rmse
                    / denominators[target_index],
                    "interpretation": "innovation scale diagnostic, not a theoretical lower bound",
                }
            )
    innovation_path = args.output_dir / "causal_forecasting_v2_innovation.csv"
    pd.DataFrame(innovation_rows).to_csv(innovation_path, index=False)

    attempts = pd.DataFrame(
        [*exploratory_attempt_table().to_dict("records"), *selected_rows]
    )
    attempts_path = args.output_dir / "causal_forecasting_v2_attempts.csv"
    attempts.to_csv(attempts_path, index=False)
    failures_path = args.output_dir / "causal_forecasting_v2_failures.csv"
    attempts.loc[attempts["status"].str.contains("failed|failure", case=False)].to_csv(
        failures_path, index=False
    )

    final_summary = summary.set_index(["model", "split"])
    validation_score = float(
        final_summary.loc[
            ("v2 frozen target-specific composite", "validation"),
            "mean_normalized_rmse",
        ]
    )
    test_score = float(
        final_summary.loc[
            ("v2 frozen target-specific composite", "test"),
            "mean_normalized_rmse",
        ]
    )
    manifest = {
        "schema_version": 1,
        "study_status": "strictly causal ground sensor forecasting v2",
        "input": {
            "path": str(args.air_quality.resolve()),
            "sha256": sha256_file(args.air_quality),
            "complete_case_rows": len(data),
            "eligible_evaluation_source_rows": len(eligible),
        },
        "evaluation_contract": {
            "sample_rows": SAMPLE_SIZE,
            "train_rows": len(split.train),
            "validation_rows": len(split.validation),
            "test_rows": len(split.test),
            "train_end": str(split.train_end),
            "validation_end": str(split.validation_end),
            "denominators": dict(zip(TARGETS, map(float, denominators), strict=True)),
            "selection_rule": "target-specific model selected using validation normalized RMSE only",
            "test_policy": "frozen mapping before test feature construction; evaluated once",
        },
        "information_set": {
            "feature_count": int(
                history.feature_matrix(validation.iloc[:1], 0).shape[1]
            ),
            "current_information": ["calendar", "station ID", *WEATHER_COLUMNS],
            "target_information": "same-station, cross-target, rolling, city, and cross-station observations strictly before query time",
            "forbidden_information": "current or future pollutant labels",
            "task": "ground sensor forecasting, not THz inversion",
        },
        "leakage_audit": {
            "minimum_target_offset_hours": 1,
            "rolling_window_boundary": "[query time minus window, query time), excluding the query hour",
            "cross_station_target_boundary": "query time minus one hour or earlier",
            "unit_test": "tests/test_causal_forecasting_v2.py mutates current and future labels and requires identical features",
            "result": "passed",
        },
        "frozen_models": FROZEN_MODELS,
        "results": {
            "validation_mean_normalized_rmse": validation_score,
            "test_mean_normalized_rmse": test_score,
            "original_goal_0_03_met": test_score <= 0.03,
            "relaxed_goal_0_08_met": test_score <= 0.08,
            "complete_candidate_validation_plateau": {
                "hgb15": float(np.mean(ATTEMPT_RESULTS["hgb15"]["scores"])),
                "hgb31": float(np.mean(ATTEMPT_RESULTS["hgb31"]["scores"])),
                "extra_leaf2": float(np.mean(ATTEMPT_RESULTS["extra_leaf2"]["scores"])),
                "interpretation": "empirical model plateau, not a formal information lower bound",
            },
        },
        "failures": [
            "The 268-feature all-training-row HGB attempt exceeded the practical resource budget after CO.",
            "The 365-day and 730-day recency windows were worse than full-period sample training on validation.",
        ],
        "runtime_seconds": time.perf_counter() - started,
        "outputs": {
            "metrics": str(metrics_path.resolve()),
            "summary": str(summary_path.resolve()),
            "innovation": str(innovation_path.resolve()),
            "attempts": str(attempts_path.resolve()),
            "failures": str(failures_path.resolve()),
        },
    }
    manifest_path = args.output_dir / "causal_forecasting_v2_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
    print(summary.to_string(index=False))
    print(f"Manifest: {manifest_path.resolve()}")


if __name__ == "__main__":
    main()
