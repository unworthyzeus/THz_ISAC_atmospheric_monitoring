from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.probe_design import (  # noqa: E402
    optimize_d_optimal_power,
    select_d_optimal_indices,
    uniform_probe_indices,
)


def test_uniform_probe_indices_cover_ordered_grid_and_center():
    np.testing.assert_array_equal(uniform_probe_indices(9, 1), np.array([4]))
    np.testing.assert_array_equal(uniform_probe_indices(10, 1), np.array([4]))
    np.testing.assert_array_equal(uniform_probe_indices(9, 3), np.array([0, 4, 8]))
    np.testing.assert_array_equal(uniform_probe_indices(6, 4), np.array([0, 2, 3, 5]))
    np.testing.assert_array_equal(uniform_probe_indices(4, 4), np.arange(4))


@pytest.mark.parametrize(
    ("n_candidates", "n_select"),
    [(0, 1), (4, 0), (4, 5), (True, 1), (4, 1.5)],
)
def test_uniform_probe_indices_reject_invalid_counts(n_candidates, n_select):
    with pytest.raises(ValueError):
        uniform_probe_indices(n_candidates, n_select)


def test_d_optimal_selection_is_deterministic_and_spans_parameters():
    design = np.array(
        [
            [10.0, 0.0],
            [9.0, 0.0],
            [0.0, 1.0],
            [0.0, 0.9],
        ]
    )
    variance = np.ones(4)

    first = select_d_optimal_indices(design, variance, n_select=2)
    second = select_d_optimal_indices(design, variance, n_select=2)

    np.testing.assert_array_equal(first, np.array([0, 2]))
    np.testing.assert_array_equal(second, first)
    assert np.linalg.matrix_rank(design[first]) == 2


def test_d_optimal_selection_uses_caller_supplied_noise_variance():
    design = np.ones((3, 1))
    variance = np.array([4.0, 0.25, 1.0])

    selected = select_d_optimal_indices(design, variance, n_select=3)

    np.testing.assert_array_equal(selected, np.array([1, 2, 0]))


def test_d_optimal_selection_can_preserve_physical_column_scaling():
    design = np.array(
        [
            [3.0, 0.0],
            [0.0, 1.0],
            [2.0, 1.0],
        ]
    )
    variance = np.ones(3)

    balanced = select_d_optimal_indices(design, variance, 1)
    physical_units = select_d_optimal_indices(
        design,
        variance,
        1,
        normalize_columns=False,
    )

    np.testing.assert_array_equal(balanced, np.array([2]))
    np.testing.assert_array_equal(physical_units, np.array([0]))


@pytest.mark.parametrize(
    ("design", "variance", "n_select", "kwargs"),
    [
        (np.ones(3), np.ones(3), 1, {}),
        (np.ones((3, 2)), np.ones((3, 1)), 1, {}),
        (np.ones((3, 2)), np.ones(2), 1, {}),
        (np.ones((3, 2)), np.ones(3), 4, {}),
        (np.array([[1.0], [np.nan]]), np.ones(2), 1, {}),
        (np.ones((2, 1)), np.array([1.0, 0.0]), 1, {}),
        (np.ones((2, 1)), np.array([1.0, np.inf]), 1, {}),
        (np.zeros((2, 1)), np.ones(2), 1, {}),
        (np.ones((2, 1)), np.ones(2), 0, {}),
        (np.ones((2, 1)), np.ones(2), 1, {"regularization": 0.0}),
        (np.ones((2, 1)), np.ones(2), 1, {"regularization": np.nan}),
        (np.ones((2, 1)), np.ones(2), 1, {"normalize_columns": "yes"}),
    ],
)
def test_d_optimal_selection_rejects_invalid_inputs(
    design,
    variance,
    n_select,
    kwargs,
):
    with pytest.raises(ValueError):
        select_d_optimal_indices(design, variance, n_select, **kwargs)


def test_d_optimal_power_allocation_preserves_total_and_prefers_best_tone():
    design = np.ones((3, 1))
    variance_coefficient = np.array([1.0, 4.0, 9.0])

    power = optimize_d_optimal_power(
        design,
        variance_coefficient,
        total_power=5.0,
    )

    np.testing.assert_allclose(power.sum(), 5.0, atol=1e-12)
    assert np.all(power >= 0.0)
    np.testing.assert_allclose(power, np.array([5.0, 0.0, 0.0]), atol=1e-7)


def test_d_optimal_power_allocation_balances_orthogonal_equal_tones():
    power = optimize_d_optimal_power(
        np.eye(2),
        np.ones(2),
        total_power=2.0,
    )

    np.testing.assert_allclose(power, np.ones(2), atol=1e-10)


@pytest.mark.parametrize(
    ("design", "coefficient", "total_power", "kwargs"),
    [
        (np.ones(2), np.ones(2), 1.0, {}),
        (np.ones((2, 1)), np.ones(1), 1.0, {}),
        (np.ones((2, 1)), np.array([1.0, 0.0]), 1.0, {}),
        (np.ones((2, 1)), np.ones(2), 0.0, {}),
        (np.zeros((2, 1)), np.ones(2), 1.0, {}),
        (np.ones((2, 1)), np.ones(2), 1.0, {"tolerance": 0.0}),
        (np.ones((2, 1)), np.ones(2), 1.0, {"max_iterations": 0}),
    ],
)
def test_d_optimal_power_allocation_rejects_invalid_inputs(
    design,
    coefficient,
    total_power,
    kwargs,
):
    with pytest.raises(ValueError):
        optimize_d_optimal_power(design, coefficient, total_power, **kwargs)
