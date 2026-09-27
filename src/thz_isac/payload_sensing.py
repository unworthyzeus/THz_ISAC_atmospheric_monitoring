"""Passive constant modulus payload sensing with explicit noise accounting.

Second/fourth moment power separation is established M2M4 estimation, not a
new estimator. Its use here avoids decoded-bit assumptions and supplies an
additional absorption observable from existing communication payloads.
"""
import math
import numpy as np

DB = 10 / np.log(10)


def _positive(value, name):
    a = np.asarray(value, dtype=float)
    if not np.isfinite(a).all() or np.any(a <= 0):
        raise ValueError(f"{name} must be finite and positive")
    return a


def _count(value):
    if isinstance(value, bool) or not np.isscalar(value) or not np.isfinite(value) or int(value) != value or value < 2:
        raise ValueError("At least two independent symbols are required")
    return int(value)


def resource_counts(elapsed_s, *, symbol_duration_s=1e-6,
                    frame_symbols=10000, pilot_symbols=30):
    """Count only complete frames, preserving the modem's existing schedule."""
    _positive(elapsed_s, "Duration")
    _positive(symbol_duration_s, "Symbol duration")
    _count(frame_symbols)
    _count(pilot_symbols)
    if pilot_symbols >= frame_symbols:
        raise ValueError("Payload symbols must remain in the frame")
    frames = int(np.floor(elapsed_s / (symbol_duration_s * frame_symbols)))
    if frames == 0:
        raise ValueError("Duration contains no complete frame")
    return dict(frames=frames, pilots=frames * pilot_symbols,
                payload=frames * (frame_symbols - pilot_symbols),
                total=frames * frame_symbols,
                charged_duration_s=frames * frame_symbols * symbol_duration_s)


def power_moments(signal_power, noise_power):
    """E[|sqrt(S) x + w|^(2k)], k=1..4, |x|=1, w~CN(0,V)."""
    s, v = np.broadcast_arrays(_positive(signal_power, "Signal power"),
                               _positive(noise_power, "Noise power"))
    return np.stack([sum(math.factorial(k) * math.comb(k, j) / math.factorial(j)
                         * s**j * v**(k-j) for j in range(k+1))
                     for k in range(1, 5)], axis=-1)


def moment_power(mean_power, mean_power_squared, symbols):
    """Estimate S and V from sample means of |y|² and |y|⁴.

    The cross-sample correction makes the estimate of S² unbiased, not its
    square root or logarithm. Invalid moment inversions remain NaN and must
    count as failed retrievals; they must never be clipped into detections.
    """
    n = _count(symbols)
    m2, m4 = np.broadcast_arrays(np.asarray(mean_power, float),
                                np.asarray(mean_power_squared, float))
    if not np.isfinite(m2).all() or not np.isfinite(m4).all() or np.any(m2 < 0) or np.any(m4 < m2*m2*(1-1e-12)):
        raise ValueError("Inconsistent finite sample moments")
    signal_squared = 2 * (n*m2*m2 - m4) / (n-1) - m4
    valid = (signal_squared > 0) & (signal_squared <= m2*m2)
    signal = np.sqrt(np.where(valid, signal_squared, np.nan))
    return signal, m2-signal, valid


def attenuation_from_moments(mean_power, mean_power_squared, symbols,
                             reference_signal_power):
    """Reference is calibrated signal power, not total signal plus noise."""
    reference = _positive(reference_signal_power, "Reference signal power")
    signal, noise, valid = moment_power(mean_power, mean_power_squared, symbols)
    return -DB*np.log(signal/reference), noise, valid


def attenuation_variance(snr, symbols, method):
    """Local asymptotic dB variance, with receiver noise fixed or estimated.

    M2M4 delta-method variance follows from noncentral chi-square moments.
    Unlike the coherent oracle, it needs neither known payload bits nor phase.
    Persistent receiver/atmosphere calibration error is additional.
    """
    s = _positive(snr, "SNR")
    n = _count(symbols)
    if method == "coherent":
        factor = 2/s
    elif method == "energy_known_noise":
        factor = 2/s + 1/s**2
    elif method == "m2m4":
        factor = 2/s + 1/s**2 + 4/s**3 + 1/s**4
    else:
        raise ValueError("Unknown observation method")
    return DB**2 * factor / n


def draw_attenuation(rng, attenuation_db, snr, symbols, draws, method,
                     noise_scale=1.):
    """Generate instrument response controls from constant modulus AWGN.

    Pilot mean and known-noise energy draws are exact. M2M4 uses the joint
    central limit distribution of its two sample moments, followed by the
    nonlinear moment inversion. This approximation is explicit and is checked
    separately against raw complex-symbol Monte Carlo. Noise-scale stress is
    unknown to the known-noise energy method; M2M4 estimates it from data.
    """
    s = _positive(snr, "SNR")
    a = np.asarray(attenuation_db, float)
    if s.ndim != 1 or a.shape != s.shape or not np.isfinite(a).all():
        raise ValueError("Matching finite spectral vectors required")
    n = _count(symbols)
    _count(draws)
    v = np.broadcast_to(_positive(noise_scale, "Noise scale"), s.shape)
    signal = s * 10**(-a/10)
    shape = (draws, len(s))
    if method == "coherent":
        z = np.sqrt(signal) + np.sqrt(v/(2*n)) * (
            rng.normal(size=shape) + 1j*rng.normal(size=shape))
        return -DB*np.log(np.abs(z)**2/s), np.ones(shape, dtype=bool)
    if method == "energy_known_noise":
        energy = v*rng.noncentral_chisquare(2*n, 2*n*signal/v, size=shape)/(2*n)
        recovered = energy - 1.  # Declared reference noise, not stress truth.
        valid = recovered > 0
        return -DB*np.log(np.where(valid, recovered/s, np.nan)), valid
    if method != "m2m4":
        raise ValueError("Unknown observation method")
    m = power_moments(signal, v)
    c11 = m[:, 1]-m[:, 0]**2
    c12 = m[:, 2]-m[:, 0]*m[:, 1]
    c22 = m[:, 3]-m[:, 1]**2
    z1, z2 = rng.normal(size=(2, *shape))
    m2 = m[:, 0] + np.sqrt(c11/n)*z1
    m4 = m[:, 1] + (c12/np.sqrt(c11)*z1
                    + np.sqrt(np.maximum(0., c22-c12*c12/c11))*z2)/np.sqrt(n)
    result, _, valid = attenuation_from_moments(m2, m4, n, s)
    return result, valid
