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

from thz_isac.spectral_model_stability import (  # noqa: E402
    compose_per_target_predictions,
    regression_metric_arrays,
    select_models_per_target,
    summarize_stability_metrics,
)

from scripts.run_spectral_model_stability import (  # noqa: E402
    COMPOSITE_CANDIDATE_ORDER,
    ELASTIC_NET_CONFIG,
    HISTOGRAM_BOOSTING_CONFIG,
    NOISE_SEEDS,
    PRIMARY_NOISE_SEED,
    RIDGE_ALPHAS,
)


def test_regression_metrics_use_supplied_target_ranges():
    truth = np.array([[0.0, 2.0], [2.0, 4.0]])
    prediction = np.array([[1.0, 2.0], [1.0, 2.0]])
    metrics = regression_metric_arrays(truth, prediction, np.array([2.0, 4.0]))

    assert metrics.rmse == pytest.approx([1.0, np.sqrt(2.0)])
    assert metrics.normalized_rmse == pytest.approx([0.5, np.sqrt(2.0) / 4.0])
    assert metrics.r2 == pytest.approx([0.0, -1.0])
    assert metrics.bias == pytest.approx([0.0, -1.0])


def test_validation_only_selection_and_composition_are_target_specific():
    truth = np.zeros((3, 2))
    predictions = {
        "first": np.array([[0.0, 2.0], [0.0, 2.0], [0.0, 2.0]]),
        "second": np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]]),
    }
    selected = select_models_per_target(
        truth,
        predictions,
        denominators=np.ones(2),
        candidate_order=("first", "second"),
    )

    assert selected == ("first", "second")
    composite = compose_per_target_predictions(selected, predictions)
    assert np.array_equal(composite, np.zeros((3, 2)))


def test_validation_selection_uses_candidate_order_to_break_ties():
    truth = np.zeros((2, 1))
    tied = {
        "preferred": np.ones((2, 1)),
        "later": -np.ones((2, 1)),
    }

    selected = select_models_per_target(
        truth,
        tied,
        denominators=np.ones(1),
        candidate_order=("preferred", "later"),
    )

    assert selected == ("preferred",)


def test_stability_summary_compares_each_seed_with_reference():
    rows = []
    for seed, reference_values, candidate_values in (
        (1, (0.4, 0.2), (0.3, 0.1)),
        (2, (0.3, 0.1), (0.4, 0.2)),
    ):
        for model, role, values in (
            ("ridge", "reference", reference_values),
            ("candidate", "candidate", candidate_values),
        ):
            for target, value in zip(("A", "B"), values, strict=True):
                rows.append(
                    {
                        "noise_seed": seed,
                        "model": model,
                        "model_role": role,
                        "configuration_status": "frozen",
                        "target": target,
                        "validation_normalized_rmse": value + 0.01,
                        "test_normalized_rmse": value,
                        "test_r2": 0.0,
                    }
                )
    summary = summarize_stability_metrics(
        pd.DataFrame(rows),
        reference_model="ridge",
        primary_seed=1,
    )
    candidate = summary.loc[
        (summary["model"] == "candidate")
        & (summary["aggregation"] == "overall_mean_across_targets")
    ].iloc[0]

    assert candidate["mean_test_normalized_rmse"] == pytest.approx(0.25)
    assert candidate["mean_test_delta_vs_reference"] == pytest.approx(0.0)
    assert candidate["test_seed_wins_vs_reference"] == 1
    assert candidate["primary_seed_test_normalized_rmse"] == pytest.approx(0.2)


def test_metric_validation_rejects_nonpositive_denominator():
    with pytest.raises(ValueError, match="strictly positive"):
        regression_metric_arrays(
            np.zeros((2, 1)),
            np.zeros((2, 1)),
            np.zeros(1),
        )


def test_predeclared_stability_design_is_frozen():
    assert NOISE_SEEDS == tuple(range(20260715, 20260725))
    assert PRIMARY_NOISE_SEED == 20260715
    assert RIDGE_ALPHAS[-3:] == (1_000_000.0, 10_000_000.0, 100_000_000.0)
    assert ELASTIC_NET_CONFIG["alpha"] == 0.01
    assert ELASTIC_NET_CONFIG["l1_ratio"] == 0.8
    assert HISTOGRAM_BOOSTING_CONFIG["max_leaf_nodes"] == 7
    assert HISTOGRAM_BOOSTING_CONFIG["l2_regularization"] == 10.0
    assert COMPOSITE_CANDIDATE_ORDER == (
        "histogram_gradient_boosting_frozen",
        "exploratory_pca_knn_component",
        "exploratory_targetwise_ridge_component",
        "multitask_elastic_net_frozen",
    )
