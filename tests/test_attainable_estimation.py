import numpy as np
import pytest
from thz_isac.attainable_estimation import (efficient_linear_estimator, bias_and_rmse,
    worst_case_calibration_rmse, calibration_allowance)

def test_known_slope_with_unknown_offset():
    x=np.arange(-2,3,dtype=float)[:,None]
    est=efficient_linear_estimator(x,np.ones((5,1)),4*np.eye(5))
    np.testing.assert_allclose(est.operator,x.T/10,atol=1e-14)
    np.testing.assert_allclose(est.covariance,[[.4]],atol=1e-14)
    np.testing.assert_allclose(est.operator@np.ones(5),0,atol=1e-14)

def test_target_confounded_with_nuisance_is_rejected():
    with pytest.raises(ValueError,match='unidentifiable'):
        efficient_linear_estimator(np.ones((5,1)),np.ones((5,1)),np.eye(5))

def test_targetwise_worst_case_is_attained():
    d=np.column_stack((np.arange(6),np.arange(6)**2))
    est=efficient_linear_estimator(d,np.ones((6,1)),np.eye(6))
    for j in range(2):
        b=.1*np.sign(est.operator[j])
        _,rmse=bias_and_rmse(est,b)
        assert rmse[j]==pytest.approx(worst_case_calibration_rmse(est,.1)[j])

def test_correlated_covariance_and_duplicate_nuisance():
    rng=np.random.default_rng(14); d=rng.normal(size=(20,2))
    n=np.column_stack((np.ones(20),2*np.ones(20)))
    sigma=np.eye(20)+.3*np.ones((20,20))
    est=efficient_linear_estimator(d,n,sigma)
    assert est.nuisance_rank==1
    np.testing.assert_allclose(est.operator@d,np.eye(2),atol=1e-12)
    np.testing.assert_allclose(est.operator@n,0,atol=1e-12)
    assert np.isnan(calibration_allowance(est,[1e-10,1e-10])).all()
