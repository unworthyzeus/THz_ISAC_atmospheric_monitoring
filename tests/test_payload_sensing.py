import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from thz_isac.payload_sensing import (DB, power_moments, moment_power,
    attenuation_variance, resource_counts, draw_attenuation)


def test_resource_accounting_does_not_create_symbols():
    c = resource_counts(10)
    assert c["pilots"] == 30000 and c["payload"] == 9970000
    assert c["total"] == c["pilots"] + c["payload"]
    cp = resource_counts(10, symbol_duration_s=1.0625e-6)
    assert cp["total"] == 9410000
    assert cp["charged_duration_s"] <= 10
    with pytest.raises(ValueError):
        resource_counts(1e-9)


def test_population_identity_and_noise_separation():
    s, v = np.array([.3, 3., 10.]), np.array([.7, 2., .2])
    m = power_moments(s, v)
    np.testing.assert_allclose(2*m[:, 0]**2-m[:, 1], s*s)
    recovered, noise, valid = moment_power(m[:, 0], m[:, 1], 10**12)
    np.testing.assert_allclose(recovered, s, rtol=1e-9)
    np.testing.assert_allclose(noise, v, rtol=1e-9)
    assert valid.all()


def test_variance_against_independent_moment_jacobian():
    for s in [.5, 3., 10., 100.]:
        m = power_moments(s, 1.)
        covariance = np.array([[m[1]-m[0]**2, m[2]-m[0]*m[1]],
                               [m[2]-m[0]*m[1], m[3]-m[1]**2]])
        gradient = -DB/s * np.array([2*m[0]/s, -1/(2*s)])
        actual = gradient@covariance@gradient/10000
        assert attenuation_variance(s, 10000, "m2m4") == pytest.approx(actual, rel=1e-9)


def test_invalid_estimate_is_not_clipped_to_a_signal():
    signal, noise, valid = moment_power([1.], [3.], 100)
    assert not valid[0] and np.isnan(signal[0]) and np.isnan(noise[0])
    with pytest.raises(ValueError):
        moment_power(2., 1., 100)
    with pytest.raises(ValueError):
        attenuation_variance(0., 100, "m2m4")


def test_exact_energy_response_and_noise_stress():
    rng = np.random.default_rng(27)
    a, valid = draw_attenuation(rng, np.array([.02]), np.array([5.]),
                                100000, 20000, "energy_known_noise")
    assert valid.all()
    assert abs(a.mean()-.02) < .0002
    expected = attenuation_variance(5.*10**(-.02/10), 100000, "energy_known_noise")
    assert a.var()/expected == pytest.approx(1., abs=.04)
    b, valid = draw_attenuation(rng, np.array([.02]), np.array([5.]),
                                100000, 20000, "m2m4", noise_scale=1.1)
    assert valid.all() and abs(b.mean()-.02) < .0002


def test_phase_and_payload_do_not_enter_observable():
    rng = np.random.default_rng(91)
    y = rng.normal(size=10000)+1j*rng.normal(size=10000)
    rotated = y*np.exp(1j*rng.uniform(-np.pi, np.pi, len(y)))
    np.testing.assert_allclose(np.abs(y)**2, np.abs(rotated)**2, atol=1e-14)
