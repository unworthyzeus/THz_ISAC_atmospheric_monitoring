import numpy as np
import pytest
from thz_isac.payload_information import fisher_information, attenuation_crlb, reference_difference_crlb
from thz_isac.payload_sensing import attenuation_variance, DB


def test_information_order_and_quadrature_convergence():
    s = np.array([10**.5, 5., 10., 30., 100.])
    q = attenuation_crlb(s, 1, 'qpsk')
    r = attenuation_crlb(s, 1, 'magnitude')
    oracle = 2*attenuation_variance(s, 2, 'coherent')
    moments = 2*attenuation_variance(s, 2, 'm2m4')
    assert np.all(oracle <= q*(1+1e-10))
    assert np.all(q <= r*(1+1e-10))
    assert np.all(r <= moments*(1+1e-10))
    for kind in ['qpsk', 'magnitude']:
        np.testing.assert_allclose(attenuation_crlb(s, 1, kind, 256),
                                   attenuation_crlb(s, 1, kind, 512), rtol=2e-6)
    np.testing.assert_allclose(q[-1], oracle[-1], rtol=1e-8)


def test_reference_is_joint_fisher_inverse():
    # Parameters: attenuation dB, log(reference power), log(noise signal),
    # log(noise reference). Independent windows share baseline power only.
    s, ref, ns, nr = 5., 8., 2000, 4000
    ts = np.array([[-1/DB, 1, 0, 0], [0, 0, 1, 0]])
    tr = np.array([[0, 1, 0, 0], [0, 0, 0, 1]])
    for kind in ['qpsk', 'magnitude']:
        j = ns*ts.T@fisher_information(s, kind)@ts+nr*tr.T@fisher_information(ref, kind)@tr
        expected = np.linalg.inv(j)[0, 0]
        assert reference_difference_crlb(s, ns, ref, nr, kind) == pytest.approx(expected)


def test_resource_scaling_and_invalid_inputs():
    one = attenuation_crlb(8., 1000)
    assert attenuation_crlb(8., 2000) == pytest.approx(one/2)
    assert reference_difference_crlb(8., 1000, 8., 1000) == pytest.approx(2*one)
    for bad in [0., -1., np.nan]:
        with pytest.raises(ValueError):
            attenuation_crlb(bad, 1000)
    with pytest.raises(ValueError):
        attenuation_crlb(8., 0)


def test_fisher_against_independent_density_derivatives():
    from scipy.integrate import quad
    from scipy.special import logsumexp
    from scipy.stats import norm, rice
    # Finite differences of library densities, integrated adaptively, do not
    # reuse the closed form score functions or their quadrature implementation.
    for kind in ['qpsk', 'magnitude']:
        s = 5.
        def logpdf(y, u, v):
            signal, noise = np.exp(u), np.exp(v)
            if kind == 'qpsk':
                a = np.sqrt(signal/2)
                return logsumexp([norm.logpdf(y, a, np.sqrt(noise/2)),
                                  norm.logpdf(y, -a, np.sqrt(noise/2))])-np.log(2)
            return rice.logpdf(y, np.sqrt(2*signal/noise), scale=np.sqrt(noise/2))
        def integrand(y, i, j):
            uv = np.array([np.log(s), 0.])
            scores = []
            for k in range(2):
                step = np.eye(2)[k]*1e-5
                scores.append((logpdf(y, *(uv+step))-logpdf(y, *(uv-step)))/2e-5)
            return scores[i]*scores[j]*np.exp(logpdf(y, *uv))
        matrix = np.array([[quad(integrand, -12 if kind == 'qpsk' else 0, 12,
                                args=(i, j), epsabs=1e-8)[0] for j in range(2)] for i in range(2)])
        if kind == 'qpsk':
            matrix *= 2
        np.testing.assert_allclose(fisher_information(s, kind), matrix, rtol=2e-7, atol=1e-8)
