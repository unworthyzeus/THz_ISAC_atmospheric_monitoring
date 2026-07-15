"""Deterministic frequency probe selection from a linear sensitivity design.

The functions in this module operate only on caller supplied sensitivities and
noise variances. In particular, they do not assume a transmit power model. For
a fair fixed total power comparison, the caller should recompute the per tone
variances for every requested number of active tones before calling the
selector.
"""

from __future__ import annotations

import operator

import numpy as np
from scipy.optimize import minimize


def _positive_integer(value: int, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer")
    try:
        result = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if result <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return result


def uniform_probe_indices(n_candidates: int, n_select: int) -> np.ndarray:
    """Return approximately uniform indices over an ordered candidate grid.

    The endpoints are included when two or more probes are requested. A single
    probe uses the lower of the two center indices when the grid length is even.
    """

    n_candidates_valid = _positive_integer(n_candidates, name="n_candidates")
    n_select_valid = _positive_integer(n_select, name="n_select")
    if n_select_valid > n_candidates_valid:
        raise ValueError("n_select cannot exceed n_candidates")

    if n_select_valid == 1:
        return np.array([(n_candidates_valid - 1) // 2], dtype=int)

    positions = np.linspace(0.0, n_candidates_valid - 1, n_select_valid)
    indices = np.floor(positions + 0.5).astype(int)
    if np.unique(indices).size != n_select_valid:
        raise RuntimeError("uniform index construction produced duplicates")
    return indices


def select_d_optimal_indices(
    design: np.ndarray,
    variance: np.ndarray,
    n_select: int,
    regularization: float = 1e-9,
    *,
    normalize_columns: bool = True,
) -> np.ndarray:
    """Greedily select candidate rows using a regularized D optimal objective.

    Parameters
    ----------
    design:
        Two dimensional sensitivity matrix with one candidate tone per row and
        one estimated parameter per column.
    variance:
        Positive noise variance for every candidate tone. These values should
        already reflect the caller's total power and active tone assumptions.
    n_select:
        Number of candidate rows to select.
    regularization:
        Positive dimensionless ridge applied relative to the mean candidate
        information. It keeps the log determinant objective defined before the
        selected rows span all parameter directions.
    normalize_columns:
        If true, balance the parameter columns to unit weighted norm before
        selection. This prevents arbitrary parameter units from controlling
        the regularized early steps.

    Returns
    -------
    numpy.ndarray
        Original row indices in greedy selection order. Ties are resolved by
        the lowest candidate index, so repeated calls are deterministic.

    Notes
    -----
    For a whitened candidate row ``a``, the marginal log determinant gain is
    ``log(1 + a.T @ information^-1 @ a)``. The implementation obtains this
    leverage through a Cholesky solve rather than forming an explicit inverse.
    """

    design_array = np.asarray(design, dtype=float)
    variance_array = np.asarray(variance, dtype=float)
    n_select_valid = _positive_integer(n_select, name="n_select")

    if design_array.ndim != 2:
        raise ValueError("design must be a two dimensional array")
    n_candidates, n_parameters = design_array.shape
    if n_candidates == 0 or n_parameters == 0:
        raise ValueError("design must contain at least one candidate and parameter")
    if variance_array.ndim != 1 or variance_array.shape[0] != n_candidates:
        raise ValueError("variance must be one dimensional with one value per design row")
    if n_select_valid > n_candidates:
        raise ValueError("n_select cannot exceed the number of candidate rows")
    if not np.all(np.isfinite(design_array)):
        raise ValueError("design must contain only finite values")
    if not np.all(np.isfinite(variance_array)) or np.any(variance_array <= 0.0):
        raise ValueError("variance must contain only finite positive values")
    if not isinstance(normalize_columns, (bool, np.bool_)):
        raise ValueError("normalize_columns must be boolean")

    try:
        regularization_valid = float(regularization)
    except (TypeError, ValueError) as exc:
        raise ValueError("regularization must be finite and positive") from exc
    if not np.isfinite(regularization_valid) or regularization_valid <= 0.0:
        raise ValueError("regularization must be finite and positive")

    whitened = design_array / np.sqrt(variance_array)[:, None]
    if not np.all(np.isfinite(whitened)):
        raise ValueError("whitened design is not finite; check design and variance scales")

    column_norms = np.linalg.norm(whitened, axis=0)
    if not np.all(np.isfinite(column_norms)) or np.any(column_norms == 0.0):
        raise ValueError("every parameter column must have nonzero finite sensitivity")
    if normalize_columns:
        whitened = whitened / column_norms

    # A global rescaling protects the information update from overflow and does
    # not change the selected rows because the ridge is scaled consistently.
    maximum = float(np.max(np.abs(whitened)))
    if not np.isfinite(maximum) or maximum == 0.0:
        raise ValueError("design must contain nonzero finite sensitivity")
    whitened = whitened / maximum

    mean_information = float(np.sum(whitened * whitened) / n_parameters)
    ridge = regularization_valid * mean_information
    if not np.isfinite(ridge) or ridge <= 0.0:
        raise ValueError("regularization is too small for the design scale")

    information = ridge * np.eye(n_parameters, dtype=float)
    selected = np.empty(n_select_valid, dtype=int)
    available = np.ones(n_candidates, dtype=bool)

    for step in range(n_select_valid):
        factor = np.linalg.cholesky(information)
        solved = np.linalg.solve(factor, whitened.T)
        leverage = np.sum(solved * solved, axis=0)
        gains = np.log1p(np.maximum(leverage, 0.0))
        gains[~available] = -np.inf

        chosen = int(np.argmax(gains))
        selected[step] = chosen
        available[chosen] = False
        row = whitened[chosen]
        information += np.outer(row, row)

    return selected


def optimize_d_optimal_power(
    design: np.ndarray,
    variance_coefficient: np.ndarray,
    total_power: float,
    regularization: float = 1e-9,
    *,
    normalize_columns: bool = True,
    tolerance: float = 1e-10,
    max_iterations: int = 1_000,
) -> np.ndarray:
    """Allocate fixed total power under an inverse power noise model.

    This helper assumes tone ``i`` has noise variance
    ``variance_coefficient[i] / allocated_power[i]``. Zero allocated power is
    interpreted as zero information. The returned nonnegative powers sum to
    ``total_power`` and maximize a regularized log determinant objective.

    Power independent residual errors are outside this simple model. A caller
    with such errors should optimize its full variance model separately.
    """

    design_array = np.asarray(design, dtype=float)
    coefficient_array = np.asarray(variance_coefficient, dtype=float)
    if design_array.ndim != 2:
        raise ValueError("design must be a two dimensional array")
    n_tones, n_parameters = design_array.shape
    if n_tones == 0 or n_parameters == 0:
        raise ValueError("design must contain at least one tone and parameter")
    if coefficient_array.ndim != 1 or coefficient_array.shape[0] != n_tones:
        raise ValueError(
            "variance_coefficient must be one dimensional with one value per design row"
        )
    if not np.all(np.isfinite(design_array)):
        raise ValueError("design must contain only finite values")
    if not np.all(np.isfinite(coefficient_array)) or np.any(coefficient_array <= 0.0):
        raise ValueError("variance_coefficient must contain only finite positive values")
    if not isinstance(normalize_columns, (bool, np.bool_)):
        raise ValueError("normalize_columns must be boolean")

    try:
        total_power_valid = float(total_power)
        regularization_valid = float(regularization)
        tolerance_valid = float(tolerance)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "total_power, regularization, and tolerance must be finite and positive"
        ) from exc
    if not np.isfinite(total_power_valid) or total_power_valid <= 0.0:
        raise ValueError("total_power must be finite and positive")
    if not np.isfinite(regularization_valid) or regularization_valid <= 0.0:
        raise ValueError("regularization must be finite and positive")
    if not np.isfinite(tolerance_valid) or tolerance_valid <= 0.0:
        raise ValueError("tolerance must be finite and positive")
    max_iterations_valid = _positive_integer(max_iterations, name="max_iterations")

    whitened = design_array / np.sqrt(coefficient_array)[:, None]
    if not np.all(np.isfinite(whitened)):
        raise ValueError("whitened design is not finite; check design and variance scales")
    column_norms = np.linalg.norm(whitened, axis=0)
    if not np.all(np.isfinite(column_norms)) or np.any(column_norms == 0.0):
        raise ValueError("every parameter column must have nonzero finite sensitivity")
    if normalize_columns:
        whitened = whitened / column_norms

    maximum = float(np.max(np.abs(whitened)))
    if not np.isfinite(maximum) or maximum == 0.0:
        raise ValueError("design must contain nonzero finite sensitivity")
    whitened = whitened / maximum

    mean_equal_power_information = float(
        np.sum(whitened * whitened) / (n_parameters * n_tones)
    )
    ridge = regularization_valid * mean_equal_power_information
    if not np.isfinite(ridge) or ridge <= 0.0:
        raise ValueError("regularization is too small for the design scale")

    identity = np.eye(n_parameters, dtype=float)

    def objective_and_gradient(fractions: np.ndarray) -> tuple[float, np.ndarray]:
        information = ridge * identity + whitened.T @ (fractions[:, None] * whitened)
        factor = np.linalg.cholesky(information)
        log_determinant = 2.0 * float(np.sum(np.log(np.diag(factor))))
        solved = np.linalg.solve(factor, whitened.T)
        gradient = np.sum(solved * solved, axis=0)
        return -log_determinant, -gradient

    initial = np.full(n_tones, 1.0 / n_tones, dtype=float)
    result = minimize(
        objective_and_gradient,
        initial,
        jac=True,
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_tones,
        constraints={
            "type": "eq",
            "fun": lambda fractions: float(np.sum(fractions) - 1.0),
            "jac": lambda fractions: np.ones(n_tones, dtype=float),
        },
        options={"ftol": tolerance_valid, "maxiter": max_iterations_valid},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"D optimal power allocation failed: {result.message}")

    fractions = np.maximum(np.asarray(result.x, dtype=float), 0.0)
    fraction_sum = float(np.sum(fractions))
    if fraction_sum <= 0.0:
        raise RuntimeError("D optimal power allocation returned zero total power")
    fractions /= fraction_sum
    return total_power_valid * fractions


__all__ = [
    "optimize_d_optimal_power",
    "select_d_optimal_indices",
    "uniform_probe_indices",
]
