"""Minimax linear estimation with atmospheric and persistent calibration errors."""
from dataclasses import dataclass
import cvxpy as cp
import numpy as np
from scipy.linalg import null_space
from .attainable_estimation import efficient_linear_estimator, LinearEstimator


@dataclass(frozen=True)
class CalibrationRobustEstimator:
    estimator: LinearEstimator
    worst_rmse: np.ndarray
    atmospheric_bias: np.ndarray
    calibration_bias: np.ndarray
    statuses: tuple
    identity_error: float


def envelope_risk(operator, variances, bias_columns, epsilon_db):
    """Exact targetwise maximum over conv(+/- bias columns) plus an L-infinity ball.

    Atmospheric and calibration worst cases may be different for different targets.
    The calibration error persists across pilots and is not a noise variance.
    """
    h = np.asarray(operator, float)
    v = np.asarray(variances, float)
    b = np.asarray(bias_columns, float)
    if epsilon_db < 0 or not np.isfinite(epsilon_db):
        raise ValueError('A finite nonnegative calibration bound is required')
    atmosphere = np.max(np.abs(h @ b), axis=1)
    calibration = epsilon_db * np.abs(h).sum(axis=1)
    return np.sqrt((h * h) @ v + (atmosphere + calibration) ** 2), atmosphere, calibration


def calibration_robust_estimator(design, nuisance, variances, bias_columns, epsilon_db):
    """Minimize variance + (max_s |h b_s| + epsilon ||h||_1)^2.

    Retain the full equality null space: bias-only rank compression is invalid
    when an arbitrary persistent spectral error contributes the L1 term.
    """
    d = np.asarray(design, float)
    n = np.asarray(nuisance, float)
    v = np.asarray(variances, float)
    b = np.asarray(bias_columns, float)
    if epsilon_db < 0 or not np.isfinite(epsilon_db):
        raise ValueError('A finite nonnegative calibration bound is required')
    if v.shape != (len(d),) or np.any(v <= 0) or not np.isfinite(v).all():
        raise ValueError('Positive finite diagonal variances are required')
    if b.ndim != 2 or b.shape[0] != len(d) or b.shape[1] == 0 or not np.isfinite(b).all():
        raise ValueError('Finite nonempty bias columns must match observations')
    base = efficient_linear_estimator(d, n, np.diag(v))
    std = np.sqrt(v)
    a = np.column_stack((d, n)) / std[:, None]
    norms = np.linalg.norm(a, axis=0)
    a = a[:, norms > 0] / norms[norms > 0]
    z_basis = null_space(a.T, rcond=1e-12)
    projected_bias = z_basis.T @ (b / std[:, None])
    operators, statuses = [], []
    for j, h0 in enumerate(base.operator):
        sd = np.sqrt(base.covariance[j, j])
        if z_basis.shape[1] == 0:
            operators.append(h0)
            statuses.append('unique_unbiased_operator')
            continue
        z = cp.Variable(z_basis.shape[1])
        atmospheric = cp.Variable(nonneg=True)
        total = cp.Variable(nonneg=True)
        scaled_h = h0 / sd + cp.multiply(1 / std, z_basis @ z)
        restrictions = [cp.abs(h0 @ b / sd + z @ projected_bias) <= atmospheric]
        restrictions.append(atmospheric + epsilon_db * cp.norm1(scaled_h) <= total)
        problem = cp.Problem(cp.Minimize(cp.sum_squares(z) + cp.square(total)), restrictions)
        problem.solve(solver='CLARABEL', tol_gap_abs=1e-9, tol_gap_rel=1e-9,
                      tol_feas=1e-9, max_iter=500)
        if problem.status != cp.OPTIMAL or z.value is None:
            raise RuntimeError(f'Calibration robust solve failed: {problem.status}')
        operators.append(h0 + sd * (z_basis @ z.value) / std)
        statuses.append(problem.status)
    h = np.asarray(operators)
    identity = float(np.max(np.abs(h @ d - np.eye(d.shape[1]))))
    if n.shape[1]:
        normalized_n = n / np.maximum(np.linalg.norm(n, axis=0), 1e-300)
        identity = max(identity, float(np.max(np.abs(h @ normalized_n))))
    if identity > 1e-7:
        raise RuntimeError(f'Equality residual too large: {identity}')
    covariance = (h * v) @ h.T
    risk, atmosphere, calibration = envelope_risk(h, v, b, epsilon_db)
    estimate = LinearEstimator(h, covariance, base.nuisance_rank, base.target_condition)
    return CalibrationRobustEstimator(estimate, risk, atmosphere, calibration,
                                      tuple(statuses), identity)


def sequential_pilot_count(duration_s, probes, pilot_duration_s=1e-6, retune_s=0.):
    """Equal integer dwell count in one sequential sweep; retuning is explicit."""
    if duration_s <= 0 or probes < 1 or pilot_duration_s <= 0 or retune_s < 0:
        raise ValueError('Invalid acquisition resources')
    available = duration_s - (probes - 1) * retune_s
    count = int(np.floor(available / (probes * pilot_duration_s)))
    if count < 1:
        raise ValueError('No complete sweep fits the acquisition budget')
    return count
