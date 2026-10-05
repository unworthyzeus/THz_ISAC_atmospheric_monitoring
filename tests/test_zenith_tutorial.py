"""Physical invariants and statistical checks for the supervisor tutorial."""
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from thz_isac.zenith_tutorial import (
    WidebandPlan, coverage_geometry, overhead_motion, differential_covariance,
    single_compound_fit, detection_summary,
)
from thz_isac.link_budget import LEOLinkBudgetConfig, compute_leo_link_budget


def test_coverage_geometry_zenith_horizon_and_triangle():
    h = 550.; r = 6371.
    zenith = coverage_geometry(90., h, r)
    assert zenith['slant_range_km'] == pytest.approx(h)
    assert zenith['coverage_area_km2'] == pytest.approx(0., abs=1e-7)
    horizon = coverage_geometry(0., h, r)
    assert horizon['slant_range_km'] == pytest.approx(np.sqrt((r+h)**2-r**2))
    assert horizon['central_angle_deg'] == pytest.approx(np.rad2deg(np.arccos(r/(r+h))))
    masks = np.array([0., 30., 60., 90.])
    values = coverage_geometry(masks)
    assert np.all(np.diff(values['coverage_area_km2']) < 0)
    assert np.allclose(values['central_angle_deg']+values['satellite_off_nadir_deg']+masks, 90.)


def test_overhead_motion_has_odd_doppler_even_range_and_matches_coverage():
    motion = overhead_motion(np.array([-5., 0., 5.]))
    assert motion['doppler_hz'][1] == 0.
    assert motion['doppler_hz'][0] == pytest.approx(-motion['doppler_hz'][2])
    assert motion['slant_range_km'][0] == pytest.approx(motion['slant_range_km'][2])
    assert motion['elevation_deg'][1] == pytest.approx(90.)
    assert np.allclose(coverage_geometry(motion['elevation_deg'])['slant_range_km'], motion['slant_range_km'])


def test_ten_ghz_is_total_bandwidth_and_both_acquisitions_are_charged():
    plan = WidebandPlan()
    assert plan.tones*plan.spacing_hz == 10e9
    assert plan.symbol_s == pytest.approx(112.4e-9)
    assert np.ptp(plan.frequencies_ghz)+plan.spacing_hz/1e9 == pytest.approx(10.)
    counts = plan.counts(20.)
    assert counts['charged_total_s'] <= 20.
    assert counts['rounding_s'] < 2*plan.frame_symbols*plan.symbol_s
    assert counts['pilots_per_tone_per_acquisition'] == counts['frames_per_acquisition']*30
    with pytest.raises(ValueError):
        plan.counts(1e-9)


@pytest.mark.parametrize('kwargs', [{'tones': True}, {'tones': 1}, {'bandwidth_hz': -1}, {'center_ghz': 400}, {'pilot_symbols': 10000}, {'cp_s': -1}])
def test_invalid_waveform_is_rejected(kwargs):
    with pytest.raises(ValueError):
        WidebandPlan(**kwargs)


def test_total_power_split_prevents_free_snr_gain_from_more_tones():
    outputs = []
    for n in (256, 1024):
        config = LEOLinkBudgetConfig(550, 25, .1, 1., 10e9/n, n_active_subcarriers=n)
        outputs.append(compute_leo_link_budget([235.], [90.], config, 10.))
    assert np.allclose(outputs[0].snr_db, outputs[1].snr_db)
    assert outputs[0].tx_power_per_subcarrier_dbm-outputs[1].tx_power_per_subcarrier_dbm == pytest.approx(10*np.log10(4))


def test_reference_noise_and_persistent_calibration_are_not_averaged_away():
    f = np.array([230., 235., 240.]); snr = np.ones(3)*.1
    thermal = differential_covariance(f, snr, 1000, 0.)
    assert thermal[0,0] == pytest.approx((20/np.log(10))**2/(1000*.1))
    c1 = differential_covariance(f, snr, 1000, .001)
    c2 = differential_covariance(f, snr, 2000, .001)
    assert np.allclose(c1-thermal, c2-thermal/2, atol=1e-15)
    attenuated = differential_covariance(f, snr, 1000, 0., enhancement_db=10.)
    assert attenuated[0,0]/thermal[0,0] == pytest.approx(5.5)


def test_estimator_rejects_gain_and_has_correct_coverage_under_gaussian_model():
    f = np.linspace(230, 240, 32)
    signature = .001*np.exp(-((f-237)/.8)**2)
    c = differential_covariance(f, np.ones(32)*10, 10000, .001)
    fit = single_compound_fit(signature, f, c)
    nuisance = np.column_stack([np.ones(32), (f-f.mean())/np.ptp(f)])
    assert (fit.operator@signature)[0] == pytest.approx(1.)
    assert np.max(abs(fit.operator@nuisance)) < 1e-9
    y = signature*3+nuisance@np.array([.2, -.03])
    assert (fit.operator@y)[0] == pytest.approx(3.)
    summary = detection_summary(fit, 0.)
    assert summary['predicted_detection_pct'] == pytest.approx(1.)
    at_limit = detection_summary(fit, summary['local_95pct_limit_ug_m3'])
    assert at_limit['predicted_detection_pct'] == pytest.approx(95.)
    # Independent repeated observations check the predicted estimator variance.
    rng = np.random.default_rng(415)
    draws = rng.multivariate_normal(signature*3, c, size=10000)@fit.operator[0]
    assert draws.var()/fit.covariance[0,0] == pytest.approx(1., abs=.04)
    assert abs(draws.mean()-3) < 4*np.sqrt(fit.covariance[0,0]/len(draws))


def test_smooth_signal_indistinguishable_from_gain_is_rejected():
    f = np.linspace(230, 240, 32)
    with pytest.raises(ValueError, match='unidentifiable'):
        single_compound_fit(np.ones(32), f, np.eye(32))
