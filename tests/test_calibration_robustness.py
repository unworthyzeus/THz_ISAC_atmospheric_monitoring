"""Independent checks of minimax risks and acquisition accounting."""
import numpy as np
import pytest
from thz_isac.calibration_robustness import (
    calibration_robust_estimator, envelope_risk, sequential_pilot_count,
)


def test_scalar_design_against_independent_dense_search():
    d = np.ones((2, 1)); n = np.empty((2, 0))
    v = np.array([1., 4.]); b = np.array([[2., -.3], [-.5, .8]])
    result = calibration_robust_estimator(d, n, v, b, .2)
    x = np.linspace(-2., 3., 200001)
    h = np.column_stack([x, 1-x])
    risk = np.sqrt((h*h)@v + (np.max(abs(h@b), axis=1)+.2*abs(h).sum(axis=1))**2)
    assert abs(result.worst_rmse[0] - risk.min()) < 2e-5
    np.testing.assert_allclose(result.estimator.operator @ d, [[1]], atol=1e-10)


def test_constructed_adversary_attains_envelope():
    h = np.array([[.4, -.7, 1.2]])
    b = np.array([[1., -2.], [3., .1], [-.5, 1.]])
    v = np.array([.1, .2, .3]); epsilon = .04
    risk, _, _ = envelope_risk(h, v, b, epsilon)
    k = int(np.argmax(abs(h@b)))
    sign = np.sign((h@b)[0, k])
    error = b[:, k] + sign*epsilon*np.sign(h[0])
    exact = np.sqrt(((h*h)@v).item()+(h@error).item()**2)
    np.testing.assert_allclose(risk[0], exact)


def test_nuisance_cancellation_and_persistent_error():
    d = np.array([[1.], [0.], [2.]])
    n = np.ones((3, 1)); b = np.array([[.1], [.2], [-.3]])
    result = calibration_robust_estimator(d, n, np.ones(3), b, .01)
    h = result.estimator.operator
    np.testing.assert_allclose(h@d, [[1]], atol=1e-9)
    np.testing.assert_allclose(h@n, [[0]], atol=1e-9)
    _, _, cal1 = envelope_risk(h, np.ones(3), b, .01)
    _, _, cal2 = envelope_risk(h, np.ones(3)/1000, b, .01)
    np.testing.assert_array_equal(cal1, cal2)


def test_sequential_time_and_retuning_are_charged():
    assert sequential_pilot_count(10, 100) == 100000
    assert sequential_pilot_count(10, 100, retune_s=.001) == 99010
    with pytest.raises(ValueError):
        sequential_pilot_count(.01, 100, retune_s=.001)
