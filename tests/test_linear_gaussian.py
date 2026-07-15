from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.linear_gaussian import (  # noqa: E402
    DB_ATTENUATION_VARIANCE_CONSTANT,
    coherent_csi_attenuation_variance_db2,
    linear_gaussian_posterior_mean,
    multi_target_regression_metrics,
    orthonormal_column_basis,
    paired_bootstrap_macro_nrmse_difference,
    select_largest_positive_scale_below_target,
    training_quantile_range,
)


def test_quantile_range_and_macro_normalized_rmse_are_per_target():
    training = np.column_stack([np.arange(1.0, 101.0), 10.0 * np.arange(1.0, 101.0)])
    denominators = training_quantile_range(training)
    truth = np.array([[1.0, 10.0], [3.0, 30.0]])
    prediction = np.array([[2.0, 20.0], [2.0, 20.0]])

    metrics = multi_target_regression_metrics(truth, prediction, denominators)

    np.testing.assert_allclose(denominators, np.array([89.1, 891.0]))
    np.testing.assert_allclose(metrics.rmse, np.array([1.0, 10.0]))
    np.testing.assert_allclose(metrics.normalized_rmse, np.array([1.0 / 89.1] * 2))
    np.testing.assert_allclose(metrics.macro_normalized_rmse, 1.0 / 89.1)
    np.testing.assert_allclose(metrics.r2, np.zeros(2))


def test_linear_gaussian_posterior_matches_scalar_closed_form():
    observations = np.array([[5.0], [-1.0]])
    design = np.array([[2.0]])
    variance = np.array([3.0])
    prior_mean = np.array([0.0])
    prior_covariance = np.array([[4.0]])

    result = linear_gaussian_posterior_mean(
        observations,
        design,
        variance,
        prior_mean,
        prior_covariance,
    )

    posterior_variance = 1.0 / (1.0 / 4.0 + 4.0 / 3.0)
    expected = observations[:, 0] * (2.0 / 3.0) * posterior_variance
    np.testing.assert_allclose(result.prediction[:, 0], expected)
    np.testing.assert_allclose(result.posterior_covariance, [[posterior_variance]])


def test_coherent_csi_variance_has_snr_scaling_and_optional_reference_term():
    base = coherent_csi_attenuation_variance_db2(
        snr_linear=100.0,
        n_pilots=10,
        residual_error_std_db=0.5,
    )
    with_reference = coherent_csi_attenuation_variance_db2(
        snr_linear=100.0,
        n_pilots=10,
        residual_error_std_db=0.5,
        reference_snr_linear=100.0,
        reference_n_pilots=10,
    )
    expected_primary = 2.0 * DB_ATTENUATION_VARIANCE_CONSTANT / 1_000.0

    np.testing.assert_allclose(base, expected_primary + 0.25)
    np.testing.assert_allclose(with_reference, 2.0 * expected_primary + 0.25)
    assert coherent_csi_attenuation_variance_db2(1_000.0, 10) < base


def test_paired_bootstrap_is_deterministic_and_preserves_pairing():
    truth = np.arange(1.0, 21.0)[:, None]
    candidate = truth.copy()
    baseline = np.zeros_like(truth)
    first = paired_bootstrap_macro_nrmse_difference(
        truth,
        candidate,
        baseline,
        np.array([10.0]),
        n_resamples=100,
        random_seed=77,
    )
    second = paired_bootstrap_macro_nrmse_difference(
        truth,
        candidate,
        baseline,
        np.array([10.0]),
        n_resamples=100,
        random_seed=77,
    )

    np.testing.assert_array_equal(first.differences, second.differences)
    assert first.observed_difference < 0.0
    assert first.confidence_upper < 0.0
    assert first.probability_candidate_better == 1.0


def test_positive_scale_selection_finds_largest_feasible_value():
    result = select_largest_positive_scale_below_target(
        lambda scale: scale**2,
        target_metric=0.25,
        lower_scale=0.01,
        upper_scale=2.0,
    )

    np.testing.assert_allclose(result.selected_scale, 0.5, rtol=1.0e-14)
    np.testing.assert_allclose(result.selected_metric, 0.25, rtol=1.0e-14)
    assert result.infeasible_scale >= result.selected_scale


def test_orthonormal_basis_removes_duplicate_and_zero_columns():
    column = np.arange(1.0, 6.0)
    matrix = np.column_stack([column, 2.0 * column, np.zeros_like(column)])

    basis = orthonormal_column_basis(matrix)

    assert basis.shape == (5, 1)
    np.testing.assert_allclose(basis.T @ basis, np.eye(1), atol=1.0e-14)
