import numpy as np
import pytest
from thz_isac.bounded_bias import bounded_bias_estimator


def test_two_sensor_analytic_bias_variance_tradeoff():
    # y1=theta+n1; y2=theta+b+n2, |b|<=B. Optimum weight on y2=1/(2+B^2).
    for bound in [0., .5, 3.]:
        d = np.ones((2, 1)); n = np.empty((2, 0)); b = np.array([[0., 0.], [bound, -bound]])
        result = bounded_bias_estimator(d, n, np.ones(2), b)
        weight = 1 / (2 + bound * bound)
        np.testing.assert_allclose(result.estimator.operator, [[1 - weight, weight]], atol=2e-6)
        np.testing.assert_allclose(result.design_rmse ** 2,
            [(1-weight)**2 + weight**2 * (1+bound**2)], atol=2e-7)


def test_exact_nuisance_cancellation_and_convex_hull_envelope():
    rng = np.random.default_rng(909500)
    d = rng.normal(size=(9, 2)); n = rng.normal(size=(9, 2)); b = rng.normal(size=(9, 5))
    r = bounded_bias_estimator(d, n, np.linspace(.5, 2., 9), b)
    np.testing.assert_allclose(r.estimator.operator @ d, np.eye(2), atol=1e-10)
    np.testing.assert_allclose(r.estimator.operator @ n, 0, atol=1e-10)
    for _ in range(100):
        weights = rng.dirichlet(np.ones(5)) * rng.choice([-1., 1.], 5)
        risk = np.sqrt(np.diag(r.estimator.covariance) + (r.estimator.operator @ (b @ weights)) ** 2)
        assert np.all(risk <= r.design_rmse + 1e-10)


def test_reject_invalid_variance():
    with pytest.raises(ValueError):
        bounded_bias_estimator(np.ones((2, 1)), np.empty((2, 0)), [1., 0.], np.ones((2, 1)))
