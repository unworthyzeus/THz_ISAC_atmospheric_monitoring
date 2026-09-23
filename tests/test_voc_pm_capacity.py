"""Scientific invariants for VOC extension, joint PM, and resource contracts."""
import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.communication_capacity import (waterfill_power, gaussian_rate_bps,
                                             check_capacity_contract)
from thz_isac.joint_voc_pm import make_joint_retrieval, fine_coarse_to_pm25_pm10
from thz_isac.physical_spectroscopy import build_layered_zenith_attenuation_design
from test_physical_spectroscopy import _processed_hitran_fixture


def test_waterfill_matches_independent_constrained_optimization():
    gain = np.array([0., 0.02, 0.4, 1., 10.])
    total = 2.0
    expected = minimize(lambda p: -np.log1p(gain*p).sum(), np.full(5,total/5),
                        bounds=[(0,total)]*5,
                        constraints={'type':'eq','fun':lambda p:p.sum()-total},
                        method='SLSQP', options={'ftol':1e-13,'maxiter':500})
    assert expected.success
    p = waterfill_power(gain,total)
    assert p.sum() == pytest.approx(total)
    assert p[0] == 0
    np.testing.assert_allclose(p, expected.x, atol=2e-7)


def test_waterfill_equal_channels_and_scaling():
    np.testing.assert_allclose(waterfill_power(np.ones(4), 2), .5)
    gain = np.array([.1, 1., 5.])
    np.testing.assert_allclose(waterfill_power(gain/1000,2000)/1000,
                               waterfill_power(gain,2))


def test_capacity_contract_rejects_extra_pilots_power_and_redistribution():
    gain = np.array([1., 10., 100.])
    p = waterfill_power(gain,1.)
    kwargs = dict(frame_symbols=1000,baseline_pilot_symbols=30,candidate_pilot_symbols=30)
    assert check_capacity_contract(gain,p,1.,1e6,**kwargs).accepted
    extra = {**kwargs,'candidate_pilot_symbols':60}
    check = check_capacity_contract(gain,p,1.,1e6,**extra)
    assert not check.accepted
    assert check.relative_loss == pytest.approx(30/970)
    assert not check_capacity_contract(gain,p*1.01,1.,1e6,**kwargs).accepted
    assert not check_capacity_contract(gain,np.full(3,1/3),1.,1e6,**kwargs).accepted
    assert not check_capacity_contract(gain,p,1.,1e6,**{**kwargs,'candidate_pilot_symbols':0}).accepted


@pytest.mark.parametrize('gain,pilots', [([-1,2],10),([1,np.nan],10),([1,2],1000),([1,2],1.5)])
def test_invalid_capacity_inputs(gain,pilots):
    with pytest.raises(ValueError):
        gaussian_rate_bps(gain,[.5,.5],1e6,frame_symbols=1000,pilot_symbols=pilots)


def test_joint_estimator_recovers_voc_and_both_pm_modes_with_nuisance():
    rng = np.random.default_rng(13)
    d = rng.uniform(size=(30,4))
    n = np.column_stack((np.ones(30),np.linspace(0,1,30)))
    model = make_joint_retrieval(d[:,:2],d[:,2:],n,np.eye(30)*.01,('H2CO','CH3OH'))
    truth = np.array([1.,2.,12.,8.])
    y = d@truth+n@np.array([.4,.2])
    estimated = model.estimate(y)
    np.testing.assert_allclose(estimated,truth,atol=1e-12)
    np.testing.assert_allclose(model.estimate_nonnegative(y),truth,atol=1e-10)
    np.testing.assert_allclose(fine_coarse_to_pm25_pm10(estimated),[12,20],atol=1e-12)
    transform = np.array([0,0,1,1])
    assert model.reported_pm_covariance()[1,1] == pytest.approx(transform@model.estimator.covariance@transform)
    assert model.spectral_fit(y)['p_value'] > .99


def test_joint_confounded_pm_rejected_instead_of_zero_error():
    x = np.linspace(0,1,20)
    with pytest.raises(ValueError,match='unidentifiable'):
        make_joint_retrieval(x[:,None],np.column_stack((x*x,2*x*x)),
                             np.ones((20,1)),np.eye(20),('H2CO',))


def test_nonnegative_fit_does_not_make_noise_into_a_detection():
    rng=np.random.default_rng(45)
    d=rng.normal(size=(40,3)); n=np.ones((40,1))
    model=make_joint_retrieval(d[:,:1],d[:,1:],n,np.eye(40),('H2CO',))
    sd=np.sqrt(np.diag(model.estimator.covariance))
    # Negative unconstrained coefficients remain visible; the bounded result
    # changes and cannot be described as an unbiased efficient estimate.
    y=d@(-sd)
    assert np.all(model.estimate(y)<0)
    assert np.all(model.estimate_nonnegative(y)>=0)


def test_spectral_fit_rejects_unmodeled_shape():
    rng=np.random.default_rng(45)
    d=rng.normal(size=(40,3)); n=np.ones((40,1))
    model=make_joint_retrieval(d[:,:1],d[:,1:],n,np.eye(40),('H2CO',))
    full=np.column_stack((d,n))
    v=rng.normal(size=40)
    residual=v-full@np.linalg.lstsq(full,v,rcond=None)[0]
    assert model.spectral_fit(100*residual)['p_value'] < 1e-10


def test_voc_target_selection_preserves_legacy_and_integrates_real_molecule_ids():
    table=_processed_hitran_fixture()
    for symbol,mid in [('H2CO',20),('CH3OH',39),('CH3CN',41)]:
        row=table.iloc[0].copy()
        row['molecule']=symbol; row['molecule_id']=mid; row['role']='target'
        table.loc[len(table)]=row
    design=build_layered_zenith_attenuation_design(table,np.linspace(60,190,20),
             n_layers=2,top_altitude_m=1000,target_gases=('H2CO','CH3OH','CH3CN'))
    assert design.gas_names == ('H2CO','CH3OH','CH3CN')
    assert design.gas_db_per_ug_m3.shape == (20,3)
    assert np.all(design.gas_db_per_ug_m3 > 0)
    with pytest.raises(ValueError,match='unique'):
        build_layered_zenith_attenuation_design(table,np.array([100]),target_gases=('CO','CO'))


def test_itu_background_resolves_absorption_bands_and_preserves_version():
    pytest.importorskip('itur')
    from itur.models import itu676
    from thz_isac.itu_background import itu676_12_layered_background
    from thz_isac.physical_spectroscopy import AtmosphereProfile
    # A homogeneous 1 km layer isolates oxygen and water band structure;
    # splitting the same air into layers must not change integrated loss.
    layer=AtmosphereProfile(np.array([0.]),np.array([1000.]),
                            np.array([288.15]),np.array([101325.]))
    split=AtmosphereProfile(np.zeros(2),np.full(2,500.),
                            np.full(2,288.15),np.full(2,101325.))
    frequency=np.array([60.,90.,150.,183.31,220.,325.153])
    kwargs=dict(surface_temperature_k=288.15,surface_dew_point_c=10.)
    old=itu676.get_version()
    itu676.change_version(11)
    try:
        loss=itu676_12_layered_background(frequency,layer,elevation_deg=90,**kwargs)
        assert itu676.get_version()==11
        assert np.all(np.isfinite(loss)) and np.all(loss>0)
        assert loss[0]>10*loss[1]  # Oxygen complex around 60 GHz.
        assert loss[3]>10*loss[2]  # Water resonance near 183 GHz.
        assert loss[5]>loss[4]
        np.testing.assert_allclose(
            itu676_12_layered_background(frequency,split,elevation_deg=30,**kwargs),
            2*loss,rtol=1e-12)
        dry=itu676_12_layered_background(frequency,layer,elevation_deg=90,
             **{**kwargs,'surface_dew_point_c':-50.})
        assert dry[3]<loss[3]/10
    finally:
        itu676.change_version(old)
