"""Tests for validation-independent advanced THz inversion helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.advanced_thz_inversion import (  # noqa: E402
    bayesian_macro_posterior_risk,
    linear_gaussian_posterior_mean_with_row_priors,
    optimize_bayesian_power_fractions,
    project_out_linear_nuisance,
    regularize_covariance,
    select_bayesian_a_optimal_indices,
    select_target_balanced_information_indices,
)
from thz_isac.linear_gaussian import (  # noqa: E402
    linear_gaussian_posterior_mean,
)


def test_row_prior_update_matches_fixed_prior_implementation() -> None:
    observations = np.array([[1.2, -0.5], [0.4, 0.7]])
    design = np.array([[1.0, 0.2], [0.1, 0.8]])
    variance = np.array([0.4, 0.7])
    prior_mean = np.array([0.3, -0.2])
    prior_covariance = np.array([[2.0, 0.3], [0.3, 1.0]])
    expected = linear_gaussian_posterior_mean(
        observations,
        design,
        variance,
        prior_mean,
        prior_covariance,
    )
    actual = linear_gaussian_posterior_mean_with_row_priors(
        observations,
        design,
        variance,
        np.broadcast_to(prior_mean, (len(observations), len(prior_mean))),
        prior_covariance,
    )
    np.testing.assert_allclose(actual.prediction, expected.prediction, rtol=1e-12)
    np.testing.assert_allclose(
        actual.posterior_covariance,
        expected.posterior_covariance,
        rtol=1e-12,
    )


def test_bayesian_a_optimal_selection_reduces_macro_risk() -> None:
    design = np.array([[4.0, 0.0], [0.0, 3.0], [0.1, 0.1]])
    variance = np.ones(3)
    prior_covariance = np.eye(2)
    denominators = np.ones(2)
    indices = select_bayesian_a_optimal_indices(
        design,
        variance,
        2,
        prior_covariance,
        denominators,
    )
    np.testing.assert_array_equal(indices, [0, 1])
    selected_risk = bayesian_macro_posterior_risk(
        design[indices],
        variance[indices],
        prior_covariance,
        denominators,
    )
    weak_risk = bayesian_macro_posterior_risk(
        design[[2]],
        variance[[2]],
        prior_covariance,
        denominators,
    )
    assert selected_risk < weak_risk


def test_target_balanced_selection_round_robins_target_columns() -> None:
    design = np.array(
        [
            [5.0, 0.0],
            [4.0, 0.0],
            [0.0, 6.0],
            [0.0, 3.0],
        ]
    )
    indices = select_target_balanced_information_indices(
        design,
        np.ones(4),
        4,
        np.ones(2),
    )
    np.testing.assert_array_equal(indices, [0, 2, 1, 3])


def test_power_optimizer_favors_the_more_informative_tone() -> None:
    design = np.array([[2.0], [0.5]])

    def variance(fractions: np.ndarray) -> np.ndarray:
        return 1.0 / fractions

    result = optimize_bayesian_power_fractions(
        design,
        variance,
        np.array([[1.0]]),
        np.array([1.0]),
    )
    assert result.optimizer_success
    assert result.accepted
    assert result.fractions[0] > result.fractions[1]
    assert result.optimized_risk < result.equal_power_risk
    np.testing.assert_allclose(np.sum(result.fractions), 1.0, rtol=0.0, atol=1e-12)


def test_power_optimizer_respects_relative_upper_bound() -> None:
    design = np.array([[5.0], [1.0], [0.5], [0.2]])

    def variance(fractions: np.ndarray) -> np.ndarray:
        return 1.0 / fractions

    result = optimize_bayesian_power_fractions(
        design,
        variance,
        np.array([[1.0]]),
        np.array([1.0]),
        minimum_relative_to_equal=0.1,
        maximum_relative_to_equal=2.0,
    )
    assert result.optimizer_success
    assert np.max(result.fractions) <= 0.5 + 1e-10
    assert np.min(result.fractions) >= 0.025 - 1e-10


def test_nuisance_projection_removes_any_nuisance_amplitude() -> None:
    design = np.array([[0.0], [1.0], [2.0], [4.0]])
    nuisance = np.ones((4, 1))
    base = np.array([[1.5]]) @ design.T
    first = project_out_linear_nuisance(
        base + 3.0 * nuisance.T,
        design,
        np.ones(4),
        nuisance,
    )
    second = project_out_linear_nuisance(
        base - 7.0 * nuisance.T,
        design,
        np.ones(4),
        nuisance,
    )
    assert first.nuisance_rank == 1
    np.testing.assert_allclose(first.observations, second.observations, atol=1e-12)
    np.testing.assert_allclose(first.design, second.design, atol=1e-12)
    assert first.observations.shape == (1, 3)


def test_covariance_regularization_repairs_a_singular_matrix() -> None:
    covariance = np.array([[1.0, 1.0], [1.0, 1.0]])
    repaired = regularize_covariance(covariance)
    np.linalg.cholesky(repaired)
    assert np.min(np.linalg.eigvalsh(repaired)) > 0.0
