"""Analytic controls for the new acquisition and calibration mechanisms."""
import numpy as np
import pandas as pd
import pytest
from thz_isac.no2_design import (solve_target, integer_dwell, polynomial_calibration,
    risk_components, temporal_difference_variance, characterize_calibration)


def test_continuous_dwell_known_best_sensor():
    d=np.array([[1.],[2.]]);empty=np.empty((2,0))
    result=solve_target(d,empty,empty,empty,0,target=0,
                        thermal_per_second=np.ones(2),available_s=4.)
    assert result.risk == pytest.approx(.25,abs=2e-7)
    assert result.operator @ d[:,0] == pytest.approx(1)
    assert result.continuous_dwell_s[1] == pytest.approx(4,abs=1e-5)


def test_structured_common_offset_is_cancelled_with_noise_cost():
    d=np.array([[1.],[0.]]);n=np.ones((2,1));b=np.empty((2,0));modes=n*.1
    result=solve_target(d,n,b,modes,0,target=0,variance=np.array([1.,4.]))
    np.testing.assert_allclose(result.operator,[1,-1],atol=1e-8)
    assert result.risk == pytest.approx(np.sqrt(5))
    assert result.calibration_bias < 1e-9
    boxed=risk_components(result.operator,np.array([1.,4.]),b,np.empty((2,0)),.1)
    assert boxed[3] == pytest.approx(.2)


def test_differential_noise_charges_both_readings_at_fixed_total_time():
    absolute=np.diag([1.,2.])
    # Each half-budget reading has twice the absolute variance.
    result=temporal_difference_variance(2*absolute,2*absolute)
    np.testing.assert_allclose(result,4*absolute)
    np.testing.assert_allclose(temporal_difference_variance(absolute,absolute,absolute),0)
    with pytest.raises(ValueError): temporal_difference_variance(absolute,absolute,3*absolute)


def test_spectral_reference_reuse_induces_covariance():
    contrast=np.array([[-1,1,0],[-1,0,1.]])
    np.testing.assert_allclose(contrast@np.eye(3)@contrast.T,[[2,1],[1,2]])


def test_integer_dwell_charges_switches_and_two_sweeps():
    count,resource=integer_dwell(np.array([1.,2.,0.]),.02,sweeps=2,retune_s=.001)
    assert np.all(count>=1)
    assert resource['switches']==4
    assert resource['charged_s']<=.02+1e-12
    assert resource['integration_s']==pytest.approx(.016)
    with pytest.raises(ValueError): integer_dwell(np.ones(3),.001,sweeps=2,retune_s=.001)


def test_polynomial_budget_is_subset_of_full_box():
    f=np.linspace(260,400,17);s=polynomial_calibration(f,1e-4,1e-5)
    assert np.max(abs(s).sum(1)+1e-5)<=1e-4+1e-15
    with pytest.raises(ValueError): polynomial_calibration(f,1e-5,1e-4)


def test_calibration_fit_does_not_use_test_to_set_envelope():
    time=pd.date_range('2020-01-01',periods=10,freq='min');f=np.linspace(260,400,5)
    values=np.zeros((10,5));values[8:,2]=.1
    frame=pd.DataFrame([dict(time=t,frequency_ghz=q,error_db=values[i,j])
                        for i,t in enumerate(time) for j,q in enumerate(f)])
    result=characterize_calibration(frame)
    assert result['training_residual_bound_db']==0
    assert result['summary'][-1]['residual_coverage']==0
    np.testing.assert_array_equal(result['center_db'],np.zeros(5))
    with pytest.raises(ValueError): characterize_calibration(frame.iloc[1:])


def test_reject_nonidentifiable_target_and_invalid_noise():
    d=np.ones((3,1));n=d.copy();empty=np.empty((3,0))
    with pytest.raises(ValueError): solve_target(d,n,empty,empty,0,target=0,variance=np.ones(3))
    with pytest.raises(ValueError): solve_target(d,empty,empty,empty,0,target=0,variance=np.zeros(3))
