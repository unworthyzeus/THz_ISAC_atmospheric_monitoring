"""Validation helpers for spectral estimator stability studies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RegressionMetricArrays:
    """Per target regression metrics with the study normalization."""

    rmse: np.ndarray
    normalized_rmse: np.ndarray
    r2: np.ndarray
    bias: np.ndarray


def regression_metric_arrays(
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> RegressionMetricArrays:
    """Return per target metrics after validating shapes and denominators."""
    truth_array = np.asarray(truth, dtype=float)
    prediction_array = np.asarray(prediction, dtype=float)
    denominator_array = np.asarray(denominators, dtype=float)
    if truth_array.ndim != 2:
        raise ValueError("truth must be a two dimensional array")
    if prediction_array.shape != truth_array.shape:
        raise ValueError("prediction must have the same shape as truth")
    if denominator_array.shape != (truth_array.shape[1],):
        raise ValueError("denominators must contain one value per target")
    if not np.all(np.isfinite(denominator_array)) or np.any(denominator_array <= 0.0):
        raise ValueError("denominators must be finite and strictly positive")

    error = prediction_array - truth_array
    rmse = np.sqrt(np.mean(error**2, axis=0))
    total = np.sum((truth_array - truth_array.mean(axis=0)) ** 2, axis=0)
    residual = np.sum(error**2, axis=0)
    r2 = np.full(truth_array.shape[1], np.nan, dtype=float)
    valid_total = total > 0.0
    r2[valid_total] = 1.0 - residual[valid_total] / total[valid_total]
    return RegressionMetricArrays(
        rmse=rmse,
        normalized_rmse=rmse / denominator_array,
        r2=r2,
        bias=np.mean(error, axis=0),
    )


def select_models_per_target(
    validation_truth: np.ndarray,
    validation_predictions: Mapping[str, np.ndarray],
    denominators: np.ndarray,
    candidate_order: Sequence[str],
) -> tuple[str, ...]:
    """Select one candidate per target using validation normalized RMSE only."""
    if not candidate_order:
        raise ValueError("candidate_order must be nonempty")
    if len(set(candidate_order)) != len(candidate_order):
        raise ValueError("candidate_order must not contain duplicates")
    if set(candidate_order) != set(validation_predictions):
        raise ValueError("candidate_order must name every validation prediction exactly once")

    score_rows = []
    for model_name in candidate_order:
        metrics = regression_metric_arrays(
            validation_truth,
            validation_predictions[model_name],
            denominators,
        )
        score_rows.append(metrics.normalized_rmse)
    score_matrix = np.vstack(score_rows)
    selected_indices = np.argmin(score_matrix, axis=0)
    return tuple(candidate_order[index] for index in selected_indices)


def compose_per_target_predictions(
    selected_models: Sequence[str],
    predictions: Mapping[str, np.ndarray],
) -> np.ndarray:
    """Assemble target columns from preselected candidate predictions."""
    if not predictions:
        raise ValueError("predictions must be nonempty")
    first_prediction = np.asarray(next(iter(predictions.values())), dtype=float)
    if first_prediction.ndim != 2:
        raise ValueError("prediction arrays must be two dimensional")
    if len(selected_models) != first_prediction.shape[1]:
        raise ValueError("selected_models must contain one name per target")

    normalized_predictions: dict[str, np.ndarray] = {}
    for model_name, prediction in predictions.items():
        prediction_array = np.asarray(prediction, dtype=float)
        if prediction_array.shape != first_prediction.shape:
            raise ValueError("all prediction arrays must have the same shape")
        normalized_predictions[model_name] = prediction_array

    composite = np.empty_like(first_prediction)
    for target_index, model_name in enumerate(selected_models):
        if model_name not in normalized_predictions:
            raise ValueError(f"Unknown selected model: {model_name}")
        composite[:, target_index] = normalized_predictions[model_name][:, target_index]
    return composite


def summarize_stability_metrics(
    detailed: pd.DataFrame,
    reference_model: str,
    primary_seed: int,
) -> pd.DataFrame:
    """Summarize per seed detailed metrics overall and by target."""
    required = {
        "noise_seed",
        "model",
        "model_role",
        "configuration_status",
        "target",
        "validation_normalized_rmse",
        "test_normalized_rmse",
        "test_r2",
    }
    missing = sorted(required - set(detailed.columns))
    if missing:
        raise ValueError(f"Detailed metrics are missing columns: {missing}")
    if reference_model not in set(detailed["model"]):
        raise ValueError(f"Reference model is absent: {reference_model}")
    duplicated = detailed.duplicated(["noise_seed", "model", "target"])
    if duplicated.any():
        raise ValueError("Detailed metrics contain duplicate seed, model, and target rows")

    model_order = list(dict.fromkeys(detailed["model"].astype(str)))
    target_order = list(dict.fromkeys(detailed["target"].astype(str)))
    rows: list[dict[str, object]] = []
    for model_name in model_order:
        model_rows = detailed.loc[detailed["model"] == model_name]
        role_values = model_rows["model_role"].unique()
        status_values = model_rows["configuration_status"].unique()
        if len(role_values) != 1 or len(status_values) != 1:
            raise ValueError(f"Model metadata is inconsistent for {model_name}")

        overall = (
            model_rows.groupby("noise_seed", as_index=False)
            .agg(
                validation_normalized_rmse=("validation_normalized_rmse", "mean"),
                test_normalized_rmse=("test_normalized_rmse", "mean"),
                test_r2=("test_r2", "mean"),
            )
            .sort_values("noise_seed")
        )
        reference_overall = (
            detailed.loc[detailed["model"] == reference_model]
            .groupby("noise_seed", as_index=False)
            .agg(reference_test_normalized_rmse=("test_normalized_rmse", "mean"))
        )
        rows.append(
            _summary_row(
                model_name,
                str(role_values[0]),
                str(status_values[0]),
                "overall_mean_across_targets",
                "all",
                overall,
                reference_overall,
                primary_seed,
            )
        )

        for target_name in target_order:
            target_rows = model_rows.loc[
                model_rows["target"] == target_name,
                [
                    "noise_seed",
                    "validation_normalized_rmse",
                    "test_normalized_rmse",
                    "test_r2",
                ],
            ].sort_values("noise_seed")
            reference_target = detailed.loc[
                (detailed["model"] == reference_model)
                & (detailed["target"] == target_name),
                ["noise_seed", "test_normalized_rmse"],
            ].rename(columns={"test_normalized_rmse": "reference_test_normalized_rmse"})
            rows.append(
                _summary_row(
                    model_name,
                    str(role_values[0]),
                    str(status_values[0]),
                    "per_target",
                    target_name,
                    target_rows,
                    reference_target,
                    primary_seed,
                )
            )
    return pd.DataFrame(rows)


def _summary_row(
    model_name: str,
    model_role: str,
    configuration_status: str,
    aggregation: str,
    target: str,
    values: pd.DataFrame,
    reference: pd.DataFrame,
    primary_seed: int,
) -> dict[str, object]:
    merged = values.merge(reference, on="noise_seed", how="inner", validate="one_to_one")
    if len(merged) != len(values):
        raise ValueError("Reference model does not cover every model seed")
    delta = merged["test_normalized_rmse"] - merged["reference_test_normalized_rmse"]
    primary = merged.loc[merged["noise_seed"] == primary_seed, "test_normalized_rmse"]
    if len(primary) != 1:
        raise ValueError(f"Primary seed {primary_seed} is missing or duplicated")
    return {
        "model": model_name,
        "model_role": model_role,
        "configuration_status": configuration_status,
        "aggregation": aggregation,
        "target": target,
        "noise_seed_count": int(len(merged)),
        "mean_validation_normalized_rmse": float(merged["validation_normalized_rmse"].mean()),
        "std_validation_normalized_rmse_across_seeds": float(
            merged["validation_normalized_rmse"].std(ddof=1)
        ),
        "mean_test_normalized_rmse": float(merged["test_normalized_rmse"].mean()),
        "std_test_normalized_rmse_across_seeds": float(
            merged["test_normalized_rmse"].std(ddof=1)
        ),
        "min_test_normalized_rmse": float(merged["test_normalized_rmse"].min()),
        "max_test_normalized_rmse": float(merged["test_normalized_rmse"].max()),
        "mean_test_r2": float(merged["test_r2"].mean()),
        "mean_test_delta_vs_reference": float(delta.mean()),
        "std_test_delta_vs_reference": float(delta.std(ddof=1)),
        "test_seed_wins_vs_reference": int((delta < 0.0).sum()),
        "test_seed_ties_vs_reference": int(np.isclose(delta, 0.0, rtol=0.0, atol=1e-15).sum()),
        "primary_seed_test_normalized_rmse": float(primary.iloc[0]),
    }
