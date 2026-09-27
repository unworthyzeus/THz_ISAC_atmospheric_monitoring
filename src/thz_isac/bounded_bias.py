"""Linear estimation minimizing worst MSE on a declared finite bias envelope."""
from dataclasses import dataclass
import cvxpy as cp
import numpy as np
from scipy.linalg import null_space
from .attainable_estimation import efficient_linear_estimator, LinearEstimator


@dataclass(frozen=True)
class BoundedBiasEstimator:
    estimator: LinearEstimator
    design_rmse: np.ndarray
    statuses: tuple
    maximum_identity_error: float


def bounded_bias_estimator(design, nuisance, variances, bias_columns):
    """Minimize h Sigma h.T + max_s (h b_s)^2, with h D=e_j and h N=0.

    A whitened null-space parameterization preserves the equality constraints.
    The guarantee covers the symmetric convex hull of the supplied biases only.
    Physical model mismatch outside that set is evaluated separately.
    """
    d = np.asarray(design, dtype=float); n = np.asarray(nuisance, dtype=float)
    variance = np.asarray(variances, dtype=float); b = np.asarray(bias_columns, dtype=float)
    if variance.shape != (len(d),) or np.any(variance <= 0) or not np.isfinite(variance).all():
        raise ValueError('Strictly positive finite diagonal variances are required')
    if b.ndim != 2 or b.shape[0] != len(d) or b.shape[1] == 0 or not np.isfinite(b).all():
        raise ValueError('Finite, nonempty bias columns must match the observations')
    nominal = efficient_linear_estimator(d, n, np.diag(variance))
    std = np.sqrt(variance)
    constraints = np.column_stack([d, n]) / std[:, None]
    norms = np.linalg.norm(constraints, axis=0)
    constraints = constraints[:, norms > 0] / norms[norms > 0]
    null = null_space(constraints.T, rcond=1e-12)
    bw = b / std[:, None]
    projected = null.T @ bw
    # Numerical rank compression removes directions with negligible bias response.
    u, singular, _ = np.linalg.svd(projected, full_matrices=False)
    keep = singular > (singular[0] * 1e-10 if len(singular) else 0)
    null = null @ u[:, keep]
    projected = null.T @ bw
    operators = []; statuses = []
    for j, h0 in enumerate(nominal.operator):
        sd = np.sqrt(nominal.covariance[j, j])
        if null.shape[1] == 0:
            operators.append(h0.copy()); statuses.append('no_bias_correction_direction')
            continue
        z = cp.Variable(null.shape[1]); t = cp.Variable(nonneg=True)
        base = h0 @ b / sd
        problem = cp.Problem(cp.Minimize(cp.sum_squares(z) + cp.square(t)),
                             [cp.abs(base + z @ projected) <= t])
        problem.solve(solver='CLARABEL', tol_gap_abs=1e-8, tol_gap_rel=1e-8,
                      tol_feas=1e-8, max_iter=300)
        if problem.status != cp.OPTIMAL or z.value is None:
            raise RuntimeError(f'Bounded-bias solver failed: {problem.status}')
        operators.append(h0 + sd * (null @ z.value) / std)
        statuses.append(problem.status)
    operator = np.asarray(operators)
    covariance = (operator * variance) @ operator.T
    error = max(float(np.max(abs(operator @ d - np.eye(d.shape[1])))),
                float(np.max(abs(operator @ (n / np.maximum(np.linalg.norm(n, axis=0), 1e-300))))) if n.shape[1] else 0.)
    if error > 1e-7:
        raise RuntimeError(f'Unbiasedness/nuisance identity residual too large: {error}')
    risk = np.sqrt(np.diag(covariance) + np.max(abs(operator @ b), axis=1) ** 2)
    estimate = LinearEstimator(operator, covariance, nominal.nuisance_rank, nominal.target_condition)
    return BoundedBiasEstimator(estimate, risk, tuple(statuses), error)
