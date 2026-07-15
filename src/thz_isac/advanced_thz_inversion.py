"""Advanced linear Gaussian tools for same-time THz inversion studies.

The helpers in this module are deliberately independent of test labels. Probe
selection and power allocation use only a caller supplied physical design,
noise model, training prior covariance, and training normalization ranges.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize


@dataclass(frozen=True)
class RowPriorGaussianPrediction:
    """Posterior predictions for row-specific prior means."""

    prediction: np.ndarray
    posterior_covariance: np.ndarray
    posterior_information: np.ndarray


@dataclass(frozen=True)
class BayesianPowerAllocation:
    """A fixed-total-power allocation selected without evaluation labels."""

    fractions: np.ndarray
    equal_power_risk: float
    optimized_risk: float
    optimizer_success: bool
    accepted: bool
    message: str
    iterations: int


@dataclass(frozen=True)
class NuisanceProjection:
    """Whitened observations and design after removing linear nuisance."""

    observations: np.ndarray
    design: np.ndarray
    variance: np.ndarray
    complement_basis: np.ndarray
    nuisance_rank: int


def regularize_covariance(
    covariance: np.ndarray,
    *,
    relative_eigenvalue_floor: float = 1.0e-9,
) -> np.ndarray:
    """Return a symmetric positive-definite covariance with a small floor."""
    matrix = _finite_square_matrix("covariance", covariance)
    if (
        not np.isfinite(relative_eigenvalue_floor)
        or relative_eigenvalue_floor <= 0.0
    ):
        raise ValueError("relative_eigenvalue_floor must be strictly positive")
    symmetric = 0.5 * (matrix + matrix.T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
    floor = relative_eigenvalue_floor * scale
    adjustment = max(0.0, floor - float(np.min(eigenvalues)))
    result = symmetric + adjustment * np.eye(matrix.shape[0])
    np.linalg.cholesky(result)
    return result


def linear_gaussian_posterior_mean_with_row_priors(
    observations: np.ndarray,
    design: np.ndarray,
    noise_variance: np.ndarray,
    prior_means: np.ndarray,
    prior_covariance: np.ndarray,
) -> RowPriorGaussianPrediction:
    """Return posterior means when every row has its own prior mean.

    The shared model is ``observation = design @ target + noise``. The prior
    covariance and diagonal observation covariance are common to every row.
    """
    values = _finite_matrix("observations", observations)
    matrix = _finite_matrix("design", design)
    means = _finite_matrix("prior_means", prior_means)
    if values.shape[1] != matrix.shape[0]:
        raise ValueError("observation columns must match design rows")
    if means.shape != (values.shape[0], matrix.shape[1]):
        raise ValueError(
            "prior_means must have one row per observation and one column per target"
        )
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    covariance = regularize_covariance(prior_covariance)
    if covariance.shape[0] != matrix.shape[1]:
        raise ValueError("prior_covariance size must match the design columns")

    prior_information = np.linalg.solve(covariance, np.eye(matrix.shape[1]))
    weighted_design = matrix / variance[:, None]
    information = prior_information + matrix.T @ weighted_design
    information = 0.5 * (information + information.T)
    centered = values - means @ matrix.T
    score = centered @ weighted_design
    shift = np.linalg.solve(information, score.T).T
    posterior_covariance = np.linalg.solve(
        information,
        np.eye(matrix.shape[1]),
    )
    posterior_covariance = 0.5 * (
        posterior_covariance + posterior_covariance.T
    )
    return RowPriorGaussianPrediction(
        prediction=means + shift,
        posterior_covariance=posterior_covariance,
        posterior_information=information,
    )


def bayesian_macro_posterior_risk(
    design: np.ndarray,
    noise_variance: np.ndarray,
    prior_covariance: np.ndarray,
    denominators: np.ndarray,
) -> float:
    """Return mean posterior standard deviation in normalized target units."""
    matrix = _finite_matrix("design", design)
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    covariance = regularize_covariance(prior_covariance)
    if covariance.shape[0] != matrix.shape[1]:
        raise ValueError("prior_covariance size must match the design columns")
    scales = _positive_vector("denominators", denominators, matrix.shape[1])
    prior_information = np.linalg.solve(covariance, np.eye(matrix.shape[1]))
    information = prior_information + matrix.T @ (matrix / variance[:, None])
    posterior = np.linalg.solve(information, np.eye(matrix.shape[1]))
    posterior = 0.5 * (posterior + posterior.T)
    diagonal = np.maximum(np.diag(posterior), 0.0)
    return float(np.mean(np.sqrt(diagonal) / scales))


def select_bayesian_a_optimal_indices(
    design: np.ndarray,
    noise_variance: np.ndarray,
    n_select: int,
    prior_covariance: np.ndarray,
    denominators: np.ndarray,
) -> np.ndarray:
    """Greedily minimize normalized posterior standard deviation.

    The update uses the Gaussian posterior covariance and a Sherman Morrison
    rank-one update. Ties are deterministic and favor the lowest row index.
    """
    matrix = _finite_matrix("design", design)
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    covariance = regularize_covariance(prior_covariance)
    if covariance.shape[0] != matrix.shape[1]:
        raise ValueError("prior_covariance size must match the design columns")
    scales = _positive_vector("denominators", denominators, matrix.shape[1])
    count = _positive_integer("n_select", n_select)
    if count > matrix.shape[0]:
        raise ValueError("n_select cannot exceed the number of candidate rows")

    posterior = covariance.copy()
    selected = np.empty(count, dtype=int)
    available = np.ones(matrix.shape[0], dtype=bool)
    for step in range(count):
        projected = matrix @ posterior
        update_denominator = variance + np.einsum(
            "ij,ij->i",
            projected,
            matrix,
        )
        reduction = projected**2 / update_denominator[:, None]
        candidate_diagonal = np.maximum(
            np.diag(posterior)[None, :] - reduction,
            0.0,
        )
        risk = np.mean(np.sqrt(candidate_diagonal) / scales[None, :], axis=1)
        risk[~available] = np.inf
        chosen = int(np.argmin(risk))
        selected[step] = chosen
        available[chosen] = False
        row_projection = projected[chosen]
        posterior -= np.outer(row_projection, row_projection) / update_denominator[
            chosen
        ]
        posterior = 0.5 * (posterior + posterior.T)
    return selected


def select_target_balanced_information_indices(
    design: np.ndarray,
    noise_variance: np.ndarray,
    n_select: int,
    target_scales: np.ndarray,
) -> np.ndarray:
    """Round-robin selection of the strongest tone for each target column."""
    matrix = _finite_matrix("design", design)
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    scales = _positive_vector("target_scales", target_scales, matrix.shape[1])
    count = _positive_integer("n_select", n_select)
    if count > matrix.shape[0]:
        raise ValueError("n_select cannot exceed the number of candidate rows")
    scores = (matrix * scales[None, :]) ** 2 / variance[:, None]
    selected = np.empty(count, dtype=int)
    available = np.ones(matrix.shape[0], dtype=bool)
    for step in range(count):
        target = step % matrix.shape[1]
        candidate_scores = scores[:, target].copy()
        candidate_scores[~available] = -np.inf
        chosen = int(np.argmax(candidate_scores))
        selected[step] = chosen
        available[chosen] = False
    return selected


def optimize_bayesian_power_fractions(
    design: np.ndarray,
    variance_function: Callable[[np.ndarray], np.ndarray],
    prior_covariance: np.ndarray,
    denominators: np.ndarray,
    *,
    minimum_relative_to_equal: float = 1.0e-3,
    maximum_relative_to_equal: float | None = None,
    tolerance: float = 1.0e-11,
    max_iterations: int = 500,
) -> BayesianPowerAllocation:
    """Minimize Bayesian macro posterior risk at fixed total power.

    ``variance_function`` maps nonnegative power fractions summing to one to
    one noise variance per design row. It may represent pilot-power or coherent
    CSI likelihoods, including a power-independent residual component.
    """
    matrix = _finite_matrix("design", design)
    covariance = regularize_covariance(prior_covariance)
    if covariance.shape[0] != matrix.shape[1]:
        raise ValueError("prior_covariance size must match the design columns")
    scales = _positive_vector("denominators", denominators, matrix.shape[1])
    for name, value in (
        ("minimum_relative_to_equal", minimum_relative_to_equal),
        ("tolerance", tolerance),
    ):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be strictly positive")
    if minimum_relative_to_equal >= 1.0:
        raise ValueError("minimum_relative_to_equal must be smaller than one")
    if maximum_relative_to_equal is not None:
        if (
            not np.isfinite(maximum_relative_to_equal)
            or maximum_relative_to_equal < 1.0
        ):
            raise ValueError(
                "maximum_relative_to_equal must be at least one when supplied"
            )
        if maximum_relative_to_equal <= minimum_relative_to_equal:
            raise ValueError(
                "maximum_relative_to_equal must exceed the minimum"
            )
    iterations = _positive_integer("max_iterations", max_iterations)

    n_tones = matrix.shape[0]
    equal = np.full(n_tones, 1.0 / n_tones)

    def objective(fractions: np.ndarray) -> float:
        variance = _positive_vector(
            "variance_function result",
            variance_function(np.asarray(fractions, dtype=float)),
            n_tones,
        )
        return bayesian_macro_posterior_risk(
            matrix,
            variance,
            covariance,
            scales,
        )

    equal_risk = objective(equal)
    lower = minimum_relative_to_equal / n_tones
    upper = (
        1.0
        if maximum_relative_to_equal is None
        else maximum_relative_to_equal / n_tones
    )
    result = minimize(
        objective,
        equal,
        method="SLSQP",
        bounds=[(lower, upper)] * n_tones,
        constraints={"type": "eq", "fun": lambda values: np.sum(values) - 1.0},
        options={"ftol": tolerance, "maxiter": iterations},
    )
    candidate = np.asarray(result.x, dtype=float)
    candidate = np.clip(candidate, lower, upper)
    candidate /= np.sum(candidate)
    candidate_risk = objective(candidate)
    accepted = bool(
        result.success
        and np.isfinite(candidate_risk)
        and candidate_risk < equal_risk
    )
    if not accepted:
        candidate = equal
        candidate_risk = equal_risk
    return BayesianPowerAllocation(
        fractions=candidate,
        equal_power_risk=float(equal_risk),
        optimized_risk=float(candidate_risk),
        optimizer_success=bool(result.success),
        accepted=accepted,
        message=str(result.message),
        iterations=int(result.nit),
    )


def project_out_linear_nuisance(
    observations: np.ndarray,
    design: np.ndarray,
    noise_variance: np.ndarray,
    nuisance_design: np.ndarray,
) -> NuisanceProjection:
    """Whiten and project observations away from a nuisance column space."""
    values = _finite_matrix("observations", observations)
    matrix = _finite_matrix("design", design)
    nuisance = _finite_matrix("nuisance_design", nuisance_design)
    if values.shape[1] != matrix.shape[0]:
        raise ValueError("observation columns must match design rows")
    if nuisance.shape[0] != matrix.shape[0]:
        raise ValueError("nuisance_design rows must match design rows")
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    scale = np.sqrt(variance)
    whitened_nuisance = nuisance / scale[:, None]
    left, singular_values, _ = np.linalg.svd(
        whitened_nuisance,
        full_matrices=True,
    )
    if singular_values.size == 0:
        rank = 0
    else:
        tolerance = (
            np.finfo(float).eps
            * max(whitened_nuisance.shape)
            * singular_values[0]
        )
        rank = int(np.sum(singular_values > tolerance))
    if rank >= matrix.shape[0]:
        raise ValueError("nuisance columns leave no observation complement")
    complement = left[:, rank:]
    whitened_observations = values / scale[None, :]
    whitened_design = matrix / scale[:, None]
    transformed_observations = whitened_observations @ complement
    transformed_design = complement.T @ whitened_design
    return NuisanceProjection(
        observations=transformed_observations,
        design=transformed_design,
        variance=np.ones(transformed_design.shape[0]),
        complement_basis=complement,
        nuisance_rank=rank,
    )


def _finite_matrix(name: str, value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != 2 or min(array.shape) < 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a nonempty finite two dimensional array")
    return array


def _finite_square_matrix(name: str, value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if (
        array.ndim != 2
        or array.shape[0] != array.shape[1]
        or array.shape[0] < 1
        or not np.all(np.isfinite(array))
    ):
        raise ValueError(f"{name} must be a nonempty finite square matrix")
    return array


def _positive_vector(name: str, value: np.ndarray, size: int) -> np.ndarray:
    array = np.ravel(np.asarray(value, dtype=float))
    if (
        array.size != size
        or not np.all(np.isfinite(array))
        or np.any(array <= 0.0)
    ):
        raise ValueError(f"{name} must contain {size} finite positive values")
    return array


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result != value or result < 1:
        raise ValueError(f"{name} must be a positive integer")
    return result


__all__ = [
    "BayesianPowerAllocation",
    "NuisanceProjection",
    "RowPriorGaussianPrediction",
    "bayesian_macro_posterior_risk",
    "linear_gaussian_posterior_mean_with_row_priors",
    "optimize_bayesian_power_fractions",
    "project_out_linear_nuisance",
    "regularize_covariance",
    "select_bayesian_a_optimal_indices",
    "select_target_balanced_information_indices",
]
