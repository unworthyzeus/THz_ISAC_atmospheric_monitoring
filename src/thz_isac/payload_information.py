"""Local Fisher bounds for unknown QPSK data, power and receiver noise.

Parameters are log(signal power), log(complex noise variance). Bounds are
asymptotic regular estimation bounds, not finite sample MSE guarantees.
"""
import numpy as np
from scipy.special import roots_hermite, roots_legendre, i0e, i1e
from .payload_sensing import DB


def fisher_information(snr, observation='qpsk', order=256):
    """Per sample 2x2 Fisher matrix; marginalize random equiprobable bits.

    QPSK uses its two independent BPSK axes. Magnitude uses the Rice density.
    Unknown constant phase is orthogonal to power/noise by symmetry. Arbitrary
    untracked phase requires the magnitude bound instead of the QPSK bound.
    """
    s = np.atleast_1d(np.asarray(snr, dtype=float))
    if s.ndim != 1 or not np.isfinite(s).all() or np.any(s <= 0) or order < 16:
        raise ValueError('Positive finite SNR and quadrature order >=16 required')
    if observation == 'qpsk':
        x, weights = roots_hermite(order)
        a = np.sqrt(s[:, None]/2)
        y = a+x
        t = 2*a*y
        g = np.stack((-a*a+a*y*np.tanh(t),
                      -.5+y*y+a*a-t*np.tanh(t)), axis=-1)
        result = 2*np.einsum('nik,nij,i->nkj', g, g, weights/np.sqrt(np.pi))
    elif observation == 'magnitude':
        x, weights = roots_legendre(order)
        a = np.sqrt(s[:, None])
        lo, hi = np.maximum(0, a-10), a+10
        r = lo+(x+1)*(hi-lo)/2
        t = 2*r*a
        ratio = i1e(t)/i0e(t)
        g = np.stack((-s[:, None]+.5*t*ratio,
                      -1+r*r+s[:, None]-t*ratio), axis=-1)
        density = 2*r*np.exp(-(r-a)**2)*i0e(t)
        w = density*weights*(hi-lo)/2
        result = np.einsum('nik,nij,ni->nkj', g, g, w)
    else:
        raise ValueError('Observation must be qpsk or magnitude')
    return result[0] if np.ndim(snr) == 0 else result


def attenuation_crlb(snr, samples, observation='qpsk', order=256):
    """Attenuation dB variance bound after profiling unknown noise power."""
    if not np.isfinite(samples) or samples <= 0:
        raise ValueError('Positive finite sample count required')
    j = fisher_information(snr, observation, order)
    efficient = j[..., 0, 0]-j[..., 0, 1]**2/j[..., 1, 1]
    if np.any(efficient <= 0):
        raise ValueError('Nonpositive efficient information')
    return DB**2/(samples*efficient)


def reference_difference_crlb(snr, samples, reference_snr, reference_samples,
                              observation='qpsk', order=256):
    """Independent windows, unknown baseline power and separate noise powers.

    Profiling the shared baseline gives the sum of the two local variances.
    Reference and signal are both charged to the resource budget.
    """
    return (attenuation_crlb(snr, samples, observation, order)
            +attenuation_crlb(reference_snr, reference_samples, observation, order))
