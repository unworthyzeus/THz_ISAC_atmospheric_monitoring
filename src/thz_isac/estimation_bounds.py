"""Estimation variance, Fisher information, and linear inversion helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


DB_ATTENUATION_VARIANCE_CONSTANT = (10.0 / np.log(10.0)) ** 2
IDEAL_GAS_CONSTANT_J_MOL_K = 8.31446261815324


@dataclass(frozen=True)
class LinearCRBResult:
    """Target CRB and diagnostics for a linear heteroscedastic model."""

    fisher_information: np.ndarray
    efficient_target_information: np.ndarray
    target_covariance: np.ndarray
    target_variance: np.ndarray
    target_standard_deviation: np.ndarray
    full_parameter_rank: int
    full_parameter_count: int
    target_rank: int
    target_count: int
    nuisance_count: int
    full_condition_number: float
    target_condition_number: float
    target_identifiable: bool


@dataclass(frozen=True)
class WeightedLeastSquaresResult:
    """Estimate and diagnostics returned by weighted least squares."""

    estimate: np.ndarray
    covariance: np.ndarray
    residuals: np.ndarray
    weighted_residual_sum_squares: np.ndarray | float
    rank: int
    parameter_count: int
    condition_number: float
    full_rank: bool


def pilot_averaged_attenuation_variance_db2(
    snr_linear: np.ndarray | float,
    n_pilots: np.ndarray | int,
    residual_error_std_db: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Return pilot averaged attenuation variance in dB squared.

    The implemented observation model is

    ``c0 / Np * (1 + 1 / gamma)**2 + sigma_residual**2``

    with ``c0 = (10 / ln(10))**2`` and linear power SNR ``gamma``.
    The residual term is modeled as independent between tones. It is not a
    model for a shared calibration bias or cross frequency covariance.
    """
    gamma = _positive_array("snr_linear", snr_linear)
    pilots = _positive_array("n_pilots", n_pilots)
    if np.any(pilots != np.floor(pilots)):
        raise ValueError("n_pilots must contain positive integers")
    residual = _nonnegative_array("residual_error_std_db", residual_error_std_db)
    return DB_ATTENUATION_VARIANCE_CONSTANT / pilots * (1.0 + 1.0 / gamma) ** 2 + residual**2


def pilot_averaged_attenuation_variance_from_snr_db(
    snr_db: np.ndarray | float,
    n_pilots: np.ndarray | int,
    residual_error_std_db: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Return pilot attenuation variance when SNR is provided in dB."""
    snr = _finite_array("snr_db", snr_db)
    return pilot_averaged_attenuation_variance_db2(
        10.0 ** (snr / 10.0),
        n_pilots,
        residual_error_std_db,
    )


def linear_gaussian_fisher_information(
    design: np.ndarray,
    variance_db2: np.ndarray | float,
) -> np.ndarray:
    """Return ``X.T @ diag(1 / variance) @ X`` for independent observations."""
    matrix = _design_matrix("design", design)
    variance = _variance_vector(variance_db2, matrix.shape[0])
    weighted = matrix / np.sqrt(variance)[:, None]
    fisher = weighted.T @ weighted
    return 0.5 * (fisher + fisher.T)


def linear_attenuation_crb(
    target_design: np.ndarray,
    variance_db2: np.ndarray | float,
    nuisance_design: np.ndarray | None = None,
    rcond: float | None = None,
) -> LinearCRBResult:
    """Return target CRBs with optional linear nuisance parameters.

    Nuisance parameters are eliminated through the Fisher information Schur
    complement. This is equivalent to taking the target block of the joint
    inverse when the joint information is full rank. A nonidentifiable target
    model returns infinite standard deviations rather than finite values from
    a misleading pseudoinverse.
    """
    target = _design_matrix("target_design", target_design)
    n_observations, n_targets = target.shape
    variance = _variance_vector(variance_db2, n_observations)

    if nuisance_design is None:
        nuisance = np.empty((n_observations, 0), dtype=float)
    else:
        nuisance = _design_matrix("nuisance_design", nuisance_design)
        if nuisance.shape[0] != n_observations:
            raise ValueError("nuisance_design must have the same number of rows as target_design")

    joint = np.column_stack([target, nuisance])
    fisher = linear_gaussian_fisher_information(joint, variance)
    full_rank, full_condition = _rank_and_condition(fisher, rcond)

    target_information = fisher[:n_targets, :n_targets]
    if nuisance.shape[1]:
        cross_information = fisher[:n_targets, n_targets:]
        nuisance_information = fisher[n_targets:, n_targets:]
        nuisance_inverse = _pseudoinverse(nuisance_information, rcond)
        efficient_information = (
            target_information
            - cross_information @ nuisance_inverse @ cross_information.T
        )
    else:
        efficient_information = target_information
    efficient_information = 0.5 * (efficient_information + efficient_information.T)

    target_rank, target_condition = _rank_and_condition(efficient_information, rcond)
    identifiable = target_rank == n_targets
    if identifiable:
        target_covariance = _pseudoinverse(efficient_information, rcond)
        target_covariance = 0.5 * (target_covariance + target_covariance.T)
        target_variance = np.maximum(np.diag(target_covariance), 0.0)
        target_std = np.sqrt(target_variance)
    else:
        target_covariance = np.full((n_targets, n_targets), np.nan)
        target_variance = np.full(n_targets, np.inf)
        target_std = np.full(n_targets, np.inf)

    return LinearCRBResult(
        fisher_information=fisher,
        efficient_target_information=efficient_information,
        target_covariance=target_covariance,
        target_variance=target_variance,
        target_standard_deviation=target_std,
        full_parameter_rank=full_rank,
        full_parameter_count=joint.shape[1],
        target_rank=target_rank,
        target_count=n_targets,
        nuisance_count=nuisance.shape[1],
        full_condition_number=full_condition,
        target_condition_number=target_condition,
        target_identifiable=identifiable,
    )


def crb_detection_floor(
    crb: LinearCRBResult,
    sigma_multiplier: float = 1.0,
) -> np.ndarray:
    """Return a detection floor as a multiple of the CRB standard deviation."""
    if not np.isfinite(sigma_multiplier) or sigma_multiplier <= 0.0:
        raise ValueError("sigma_multiplier must be strictly positive")
    return sigma_multiplier * crb.target_standard_deviation


def gas_ug_m3_to_ppm(
    concentration_ug_m3: np.ndarray | float,
    molar_mass_g_mol: float,
    temperature_k: float = 298.15,
    pressure_pa: float = 101_325.0,
) -> np.ndarray:
    """Convert gas mass concentration to ppm using the ideal gas law."""
    concentration = _nonnegative_array("concentration_ug_m3", concentration_ug_m3)
    _require_positive_scalar("molar_mass_g_mol", molar_mass_g_mol)
    _require_positive_scalar("temperature_k", temperature_k)
    _require_positive_scalar("pressure_pa", pressure_pa)
    return (
        concentration
        * IDEAL_GAS_CONSTANT_J_MOL_K
        * temperature_k
        / (molar_mass_g_mol * pressure_pa)
    )


def gas_ppm_to_ug_m3(
    concentration_ppm: np.ndarray | float,
    molar_mass_g_mol: float,
    temperature_k: float = 298.15,
    pressure_pa: float = 101_325.0,
) -> np.ndarray:
    """Convert ppm to gas mass concentration using the ideal gas law."""
    concentration = _nonnegative_array("concentration_ppm", concentration_ppm)
    _require_positive_scalar("molar_mass_g_mol", molar_mass_g_mol)
    _require_positive_scalar("temperature_k", temperature_k)
    _require_positive_scalar("pressure_pa", pressure_pa)
    return (
        concentration
        * molar_mass_g_mol
        * pressure_pa
        / (IDEAL_GAS_CONSTANT_J_MOL_K * temperature_k)
    )


def gas_detection_floor_ppm(
    crb_std_ug_m3: np.ndarray | float,
    molar_mass_g_mol: float,
    temperature_k: float = 298.15,
    pressure_pa: float = 101_325.0,
) -> np.ndarray:
    """Convert a gas concentration CRB standard deviation to a ppm floor."""
    return gas_ug_m3_to_ppm(
        crb_std_ug_m3,
        molar_mass_g_mol,
        temperature_k,
        pressure_pa,
    )


def weighted_least_squares(
    design: np.ndarray,
    observations: np.ndarray,
    variance_db2: np.ndarray | float,
    rcond: float | None = None,
) -> WeightedLeastSquaresResult:
    """Solve a linear model with known independent heteroscedastic variances."""
    matrix = _design_matrix("design", design)
    values = np.asarray(observations, dtype=float)
    if values.ndim not in (1, 2) or values.shape[0] != matrix.shape[0]:
        raise ValueError("observations must have shape (n_observations,) or (n_observations, n_series)")
    if not np.all(np.isfinite(values)):
        raise ValueError("observations must contain finite values")

    variance = _variance_vector(variance_db2, matrix.shape[0])
    scale = np.sqrt(variance)
    weighted_design = matrix / scale[:, None]
    if values.ndim == 1:
        weighted_values = values / scale
    else:
        weighted_values = values / scale[:, None]

    estimate, _, rank, _ = np.linalg.lstsq(weighted_design, weighted_values, rcond=rcond)
    residuals = values - matrix @ estimate
    if residuals.ndim == 1:
        weighted_rss: np.ndarray | float = float(np.sum(residuals**2 / variance))
    else:
        weighted_rss = np.sum(residuals**2 / variance[:, None], axis=0)

    fisher = linear_gaussian_fisher_information(matrix, variance)
    covariance = _pseudoinverse(fisher, rcond)
    _, condition = _rank_and_condition(weighted_design, rcond)
    parameter_count = matrix.shape[1]
    if int(rank) < parameter_count:
        condition = float("inf")
    return WeightedLeastSquaresResult(
        estimate=estimate,
        covariance=covariance,
        residuals=residuals,
        weighted_residual_sum_squares=weighted_rss,
        rank=int(rank),
        parameter_count=parameter_count,
        condition_number=condition,
        full_rank=int(rank) == parameter_count,
    )


def _design_matrix(name: str, value: np.ndarray) -> np.ndarray:
    matrix = np.asarray(value, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 1 or matrix.shape[1] < 1:
        raise ValueError(f"{name} must be a nonempty two dimensional matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must contain finite values")
    return matrix


def _variance_vector(value: np.ndarray | float, n_observations: int) -> np.ndarray:
    variance = _positive_array("variance_db2", value)
    if variance.ndim == 0:
        return np.full(n_observations, float(variance))
    variance = np.ravel(variance)
    if variance.size != n_observations:
        raise ValueError("variance_db2 must be scalar or have one value per observation")
    return variance


def _rank_and_condition(matrix: np.ndarray, rcond: float | None) -> tuple[int, float]:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size == 0 or singular_values[0] == 0.0:
        return 0, float("inf")
    relative_cutoff = (
        max(matrix.shape) * np.finfo(float).eps
        if rcond is None
        else _validated_rcond(rcond)
    )
    tolerance = relative_cutoff * singular_values[0]
    rank = int(np.sum(singular_values > tolerance))
    full_dimension = min(matrix.shape)
    if rank < full_dimension or singular_values[-1] <= tolerance:
        condition = float("inf")
    else:
        condition = float(singular_values[0] / singular_values[-1])
    return rank, condition


def _pseudoinverse(matrix: np.ndarray, rcond: float | None) -> np.ndarray:
    if rcond is None:
        return np.linalg.pinv(matrix)
    return np.linalg.pinv(matrix, rcond=_validated_rcond(rcond))


def _validated_rcond(value: float) -> float:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError("rcond must be strictly positive")
    return float(value)


def _finite_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def _positive_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = _finite_array(name, value)
    if np.any(array <= 0.0):
        raise ValueError(f"{name} must be strictly positive")
    return array


def _nonnegative_array(name: str, value: np.ndarray | float) -> np.ndarray:
    array = _finite_array(name, value)
    if np.any(array < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    return array


def _require_positive_scalar(name: str, value: float) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
