"""Metrics and Gaussian linear inference for reproducible estimator audits."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


DB_ATTENUATION_VARIANCE_CONSTANT = (10.0 / np.log(10.0)) ** 2


@dataclass(frozen=True)
class MultiTargetRegressionMetrics:
    """Per target regression metrics with macro summary properties."""

    mae: np.ndarray
    rmse: np.ndarray
    normalized_rmse: np.ndarray
    r2: np.ndarray
    bias: np.ndarray

    @property
    def macro_normalized_rmse(self) -> float:
        """Return the unweighted mean normalized RMSE across targets."""
        return float(np.mean(self.normalized_rmse))

    @property
    def mean_r2(self) -> float:
        """Return the unweighted mean finite R2 across targets."""
        return float(np.nanmean(self.r2))


@dataclass(frozen=True)
class LinearGaussianPrediction:
    """Posterior means and covariance for a Gaussian linear model."""

    prediction: np.ndarray
    posterior_covariance: np.ndarray
    posterior_information: np.ndarray


@dataclass(frozen=True)
class PairedBootstrapResult:
    """Paired bootstrap distribution and percentile interval."""

    observed_difference: float
    confidence_lower: float
    confidence_upper: float
    probability_candidate_better: float
    differences: np.ndarray
    confidence_level: float
    random_seed: int


@dataclass(frozen=True)
class PositiveScaleSelection:
    """Largest positive scale satisfying a monotone metric threshold."""

    selected_scale: float
    selected_metric: float
    infeasible_scale: float
    infeasible_metric: float
    target_metric: float
    iterations: int


def training_quantile_range(
    targets: np.ndarray,
    lower_quantile: float = 0.05,
    upper_quantile: float = 0.95,
) -> np.ndarray:
    """Return a strictly positive per target training quantile range."""
    values = _finite_matrix("targets", targets)
    if not 0.0 <= lower_quantile < upper_quantile <= 1.0:
        raise ValueError("quantiles must satisfy 0 <= lower < upper <= 1")
    ranges = np.quantile(values, upper_quantile, axis=0) - np.quantile(
        values,
        lower_quantile,
        axis=0,
    )
    if np.any(ranges <= 0.0):
        raise ValueError("every target must have a strictly positive quantile range")
    return ranges


def multi_target_regression_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> MultiTargetRegressionMetrics:
    """Compute per target RMSE, normalized RMSE, R2, MAE, and bias."""
    actual = _finite_matrix("truth", truth)
    estimate = _finite_matrix("prediction", prediction)
    if actual.shape != estimate.shape:
        raise ValueError("truth and prediction must have identical shapes")
    scale = _positive_vector("denominators", denominators, actual.shape[1])

    error = estimate - actual
    mae = np.mean(np.abs(error), axis=0)
    rmse = np.sqrt(np.mean(error**2, axis=0))
    centered = actual - np.mean(actual, axis=0)
    total = np.sum(centered**2, axis=0)
    residual = np.sum(error**2, axis=0)
    r2 = np.full(actual.shape[1], np.nan, dtype=float)
    positive_total = total > 0.0
    r2[positive_total] = 1.0 - residual[positive_total] / total[positive_total]
    return MultiTargetRegressionMetrics(
        mae=mae,
        rmse=rmse,
        normalized_rmse=rmse / scale,
        r2=r2,
        bias=np.mean(error, axis=0),
    )


def linear_gaussian_posterior_mean(
    observations: np.ndarray,
    design: np.ndarray,
    noise_variance: np.ndarray,
    prior_mean: np.ndarray,
    prior_covariance: np.ndarray,
) -> LinearGaussianPrediction:
    """Return posterior means for ``x = design @ theta + noise``.

    Observations are supplied as rows, while ``design`` has one row per
    observed tone and one column per target. The noise covariance is diagonal.
    """
    values = _finite_matrix("observations", observations)
    matrix = _finite_matrix("design", design)
    if values.shape[1] != matrix.shape[0]:
        raise ValueError("observation columns must match design rows")
    variance = _positive_vector("noise_variance", noise_variance, matrix.shape[0])
    mean = _finite_vector("prior_mean", prior_mean, matrix.shape[1])
    covariance = _finite_square_matrix(
        "prior_covariance",
        prior_covariance,
        matrix.shape[1],
    )
    covariance = 0.5 * (covariance + covariance.T)
    try:
        np.linalg.cholesky(covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError("prior_covariance must be positive definite") from exc

    prior_information = np.linalg.solve(covariance, np.eye(matrix.shape[1]))
    measurement_information = matrix.T @ (matrix / variance[:, None])
    information = prior_information + measurement_information
    information = 0.5 * (information + information.T)
    centered = values - mean @ matrix.T
    score = centered @ (matrix / variance[:, None])
    posterior_shift = np.linalg.solve(information, score.T).T
    posterior_covariance = np.linalg.solve(information, np.eye(matrix.shape[1]))
    posterior_covariance = 0.5 * (posterior_covariance + posterior_covariance.T)
    return LinearGaussianPrediction(
        prediction=mean + posterior_shift,
        posterior_covariance=posterior_covariance,
        posterior_information=information,
    )


def coherent_csi_attenuation_variance_db2(
    snr_linear: np.ndarray | float,
    n_pilots: np.ndarray | int,
    residual_error_std_db: np.ndarray | float = 0.0,
    *,
    reference_snr_linear: np.ndarray | float | None = None,
    reference_n_pilots: np.ndarray | int | None = None,
) -> np.ndarray:
    """Return the high SNR delta method variance for coherent CSI averaging.

    The primary term is ``2*c0/(Np*SNR)`` for attenuation inferred from the
    amplitude of a coherently averaged deterministic complex channel. When a
    noisy clear sky reference is supplied, its independent variance is added.
    """
    gamma = _positive_array("snr_linear", snr_linear)
    pilots = _positive_integer_array("n_pilots", n_pilots)
    residual = _nonnegative_array("residual_error_std_db", residual_error_std_db)
    variance = 2.0 * DB_ATTENUATION_VARIANCE_CONSTANT / (pilots * gamma)

    if (reference_snr_linear is None) != (reference_n_pilots is None):
        raise ValueError(
            "reference_snr_linear and reference_n_pilots must be supplied together"
        )
    if reference_snr_linear is not None and reference_n_pilots is not None:
        reference_gamma = _positive_array(
            "reference_snr_linear",
            reference_snr_linear,
        )
        reference_pilots = _positive_integer_array(
            "reference_n_pilots",
            reference_n_pilots,
        )
        variance = variance + 2.0 * DB_ATTENUATION_VARIANCE_CONSTANT / (
            reference_pilots * reference_gamma
        )
    return variance + residual**2


def paired_bootstrap_macro_nrmse_difference(
    truth: np.ndarray,
    candidate_prediction: np.ndarray,
    baseline_prediction: np.ndarray,
    denominators: np.ndarray,
    *,
    n_resamples: int = 2_000,
    confidence_level: float = 0.95,
    random_seed: int = 4_401,
) -> PairedBootstrapResult:
    """Bootstrap candidate minus baseline macro normalized RMSE by row."""
    actual = _finite_matrix("truth", truth)
    candidate = _finite_matrix("candidate_prediction", candidate_prediction)
    baseline = _finite_matrix("baseline_prediction", baseline_prediction)
    if candidate.shape != actual.shape or baseline.shape != actual.shape:
        raise ValueError("truth and both prediction arrays must have identical shapes")
    scale = _positive_vector("denominators", denominators, actual.shape[1])
    if not isinstance(n_resamples, (int, np.integer)) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie between zero and one")

    candidate_squared_error = (candidate - actual) ** 2
    baseline_squared_error = (baseline - actual) ** 2
    observed = (
        np.mean(np.sqrt(np.mean(candidate_squared_error, axis=0)) / scale)
        - np.mean(np.sqrt(np.mean(baseline_squared_error, axis=0)) / scale)
    )
    rng = np.random.default_rng(random_seed)
    differences = np.empty(int(n_resamples), dtype=float)
    for index in range(int(n_resamples)):
        sampled = rng.integers(0, actual.shape[0], actual.shape[0])
        candidate_metric = np.mean(
            np.sqrt(np.mean(candidate_squared_error[sampled], axis=0)) / scale
        )
        baseline_metric = np.mean(
            np.sqrt(np.mean(baseline_squared_error[sampled], axis=0)) / scale
        )
        differences[index] = candidate_metric - baseline_metric

    tail = (1.0 - confidence_level) / 2.0
    lower, upper = np.quantile(differences, [tail, 1.0 - tail])
    return PairedBootstrapResult(
        observed_difference=float(observed),
        confidence_lower=float(lower),
        confidence_upper=float(upper),
        probability_candidate_better=float(np.mean(differences < 0.0)),
        differences=differences,
        confidence_level=float(confidence_level),
        random_seed=int(random_seed),
    )


def select_largest_positive_scale_below_target(
    metric_function: Callable[[float], float],
    target_metric: float,
    lower_scale: float,
    upper_scale: float,
    *,
    iterations: int = 60,
) -> PositiveScaleSelection:
    """Use geometric bisection for a nondecreasing positive scale metric."""
    for name, value in (
        ("target_metric", target_metric),
        ("lower_scale", lower_scale),
        ("upper_scale", upper_scale),
    ):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be strictly positive")
    if lower_scale >= upper_scale:
        raise ValueError("lower_scale must be smaller than upper_scale")
    if not isinstance(iterations, (int, np.integer)) or iterations < 1:
        raise ValueError("iterations must be a positive integer")

    lower = float(lower_scale)
    upper = float(upper_scale)
    lower_metric = float(metric_function(lower))
    upper_metric = float(metric_function(upper))
    if not np.isfinite(lower_metric) or not np.isfinite(upper_metric):
        raise ValueError("metric_function must return finite values")
    if lower_metric > target_metric:
        raise ValueError("lower_scale is not feasible for the requested metric")
    if upper_metric <= target_metric:
        raise ValueError("upper_scale is still feasible; increase the upper bound")

    for _ in range(int(iterations)):
        middle = float(np.sqrt(lower * upper))
        middle_metric = float(metric_function(middle))
        if not np.isfinite(middle_metric):
            raise ValueError("metric_function must return finite values")
        if middle_metric <= target_metric:
            lower = middle
            lower_metric = middle_metric
        else:
            upper = middle
            upper_metric = middle_metric

    return PositiveScaleSelection(
        selected_scale=lower,
        selected_metric=lower_metric,
        infeasible_scale=upper,
        infeasible_metric=upper_metric,
        target_metric=float(target_metric),
        iterations=int(iterations),
    )


def orthonormal_column_basis(
    matrix: np.ndarray,
    relative_tolerance: float = 1.0e-10,
) -> np.ndarray:
    """Return a stable orthonormal basis for the supplied column space."""
    values = _finite_matrix("matrix", matrix)
    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0.0:
        raise ValueError("relative_tolerance must be strictly positive")
    norms = np.linalg.norm(values, axis=0)
    nonzero = norms > 0.0
    if not np.any(nonzero):
        return np.empty((values.shape[0], 0), dtype=float)
    normalized = values[:, nonzero] / norms[nonzero]
    left, singular_values, _ = np.linalg.svd(normalized, full_matrices=False)
    keep = singular_values > singular_values[0] * relative_tolerance
    return left[:, keep]


def _finite_matrix(name: str, value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim != 2 or min(array.shape) < 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a nonempty finite two dimensional array")
    return array


def _finite_square_matrix(name: str, value: np.ndarray, size: int) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != (size, size) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite square matrix with shape {(size, size)}")
    return array


def _finite_vector(name: str, value: np.ndarray, size: int) -> np.ndarray:
    array = np.ravel(np.asarray(value, dtype=float))
    if array.size != size or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain {size} finite values")
    return array


def _positive_vector(name: str, value: np.ndarray, size: int) -> np.ndarray:
    array = _finite_vector(name, value, size)
    if np.any(array <= 0.0):
        raise ValueError(f"{name} must contain strictly positive values")
    return array


def _positive_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array <= 0.0):
        raise ValueError(f"{name} must contain finite strictly positive values")
    return array


def _positive_integer_array(name: str, value: np.ndarray | int) -> np.ndarray:
    array = _positive_array(name, value)
    if np.any(array != np.floor(array)):
        raise ValueError(f"{name} must contain positive integers")
    return array


def _nonnegative_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)) or np.any(array < 0.0):
        raise ValueError(f"{name} must contain finite nonnegative values")
    return array
