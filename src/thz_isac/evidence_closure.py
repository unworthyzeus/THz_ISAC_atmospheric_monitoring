"""Measurement-domain gates and independently inspectable closure calculations."""
import numpy as np
from scipy.linalg import solve_triangular
from scipy.stats import norm


def requirement_assessment(*, reference_domain, measured_domain, averaging_s,
                           covered_s, paired_reference, calibrated, limit_ug_m3,
                           modeled_lod_ug_m3):
    """Do not promote a favorable model sensitivity into environmental compliance.

    Coverage is a necessary duration condition, not a sufficient sampling rule.
    This function returns evidence gates; it does not issue legal certification.
    """
    if averaging_s <= 0 or covered_s < 0 or not np.isfinite([averaging_s, covered_s]).all():
        raise ValueError("Finite positive averaging time and nonnegative coverage required")
    reasons = []
    if reference_domain != measured_domain:
        reasons.append("measurement_domain_mismatch")
    if covered_s < averaging_s:
        reasons.append("averaging_period_not_covered")
    if not paired_reference:
        reasons.append("no_paired_reference_measurements")
    if not calibrated:
        reasons.append("instrument_or_forward_model_uncalibrated")
    applicable = limit_ug_m3 is not None
    if applicable and (not np.isfinite(limit_ug_m3) or limit_ug_m3 <= 0):
        raise ValueError("Positive reference concentration required")
    if not applicable:
        reasons.append("no_applicable_guideline_in_selected_sources")
    ratio = None if not applicable or modeled_lod_ug_m3 is None else modeled_lod_ug_m3 / limit_ug_m3
    return dict(evidence_complete=not reasons, reasons=reasons, modeled_lod_to_reference_ratio=ratio,
                modeled_sensitivity_sufficient=None if ratio is None else bool(ratio <= 1),
                compliance_demonstrated=False,
                interpretation="Evidence gates only; sensitivity is not compliance")


def tds_transfer(time_ps, signal, reference):
    """Unpadded FFT transfer from already corrected, uniformly sampled traces.

    The electric-field ratio gives -20 log10 |Es/Er| attenuation. No independent
    bins are manufactured by zero padding and no negative attenuation is clipped.
    """
    t, s, r = map(lambda x: np.asarray(x, dtype=float), (time_ps, signal, reference))
    if t.ndim != 1 or len(t) < 4 or s.shape != t.shape or r.shape != t.shape or not all(np.isfinite(x).all() for x in (t, s, r)):
        raise ValueError("Finite paired time traces required")
    dt = np.diff(t)
    if dt.min() <= 0 or not np.allclose(dt, dt.mean(), rtol=1e-5, atol=1e-9):
        raise ValueError("Uniform strictly increasing time grid required")
    sf, rf = np.fft.rfft(s), np.fft.rfft(r)
    f = np.fft.rfftfreq(len(t), dt.mean() * 1e-12) / 1e9
    if np.any(np.abs(rf) == 0):
        ratio = np.divide(sf, rf, out=np.full_like(sf, np.nan), where=np.abs(rf) > 0)
    else:
        ratio = sf / rf
    with np.errstate(divide="ignore", invalid="ignore"):
        attenuation = -20 * np.log10(np.abs(ratio))
    return dict(frequency_ghz=f, attenuation_db=attenuation,
                phase_rad=np.angle(ratio), sample_spectrum=sf, reference_spectrum=rf,
                resolution_ghz=float(f[1] - f[0]))


def projected_design(design, nuisance, covariance, rtol=1e-12):
    """Whiten and remove nuisance span without normal-equation inversion."""
    d, n, c = map(lambda a: np.asarray(a, dtype=float), (design, nuisance, covariance))
    if d.ndim != 2 or n.ndim != 2 or n.shape[0] != len(d) or c.shape != (len(d), len(d)) or not all(np.isfinite(x).all() for x in (d, n, c)) or not np.allclose(c, c.T):
        raise ValueError("Invalid projected-design inputs")
    chol = np.linalg.cholesky(c)
    wd = solve_triangular(chol, d, lower=True)
    wn = solve_triangular(chol, n, lower=True)
    scale = np.linalg.norm(wn, axis=0)
    wn = wn[:, scale > 0] / scale[scale > 0]
    u, singular, _ = np.linalg.svd(wn, full_matrices=False)
    rank = int(np.sum(singular > singular[0] * rtol)) if len(singular) else 0
    return wd - u[:, :rank] @ (u[:, :rank].T @ wd)


def covariance_from_information_rows(rows, rtol=1e-12):
    """SVD covariance; refuse rank loss instead of reporting zero uncertainty."""
    a = np.asarray(rows, dtype=float)
    if a.ndim != 2 or not np.isfinite(a).all() or not a.shape[1]:
        raise ValueError("Finite information rows required")
    scales = np.linalg.norm(a, axis=0)
    if np.any(scales == 0):
        raise ValueError("Unidentifiable target")
    _, s, vh = np.linalg.svd(a / scales, full_matrices=False)
    if len(s) < a.shape[1] or s[-1] <= rtol * s[0]:
        raise ValueError("Unidentifiable target")
    root = vh.T / s / scales[:, None]
    return root @ root.T


def conditional_power(concentration, standard_error, family_alpha=.01, family_size=6):
    if concentration < 0 or standard_error <= 0 or not np.isfinite([concentration, standard_error]).all():
        raise ValueError("Nonnegative concentration and positive error required")
    return float(norm.sf(norm.isf(family_alpha / family_size) - concentration / standard_error))


def ofdm_qpsk_control(snr, *, seed=20260923, frame_symbols=10000, pilot_symbols=30,
                      cp_samples=16, normalized_cfo=0.):
    """One OFDM frame with pilot channel estimation and uncoded QPSK payload.

    FFT normalization preserves specified per-tone SNR. Pilot reuse is a read-
    only consumer of the same received pilots. CFO is residual within each
    symbol after ideal common-phase tracking, not an oscillator measurement.
    """
    sn = np.asarray(snr, dtype=float)
    if sn.ndim != 1 or len(sn) < 2 or not np.isfinite(sn).all() or np.any(sn <= 0) or not 0 < pilot_symbols < frame_symbols or not 0 <= cp_samples < len(sn):
        raise ValueError("Invalid OFDM parameters")
    rng = np.random.default_rng(seed)
    n = len(sn)
    symbols = (rng.integers(0, 2, (frame_symbols, n, 2)) * 2 - 1)
    tx = (symbols[:, :, 0] + 1j * symbols[:, :, 1]) / np.sqrt(2)
    # Static frequency-selective LOS phase after timing synchronization.
    phase = np.linspace(-.2, .2, n)
    h = np.sqrt(sn) * np.exp(1j * phase)
    time = np.fft.ifft(tx * h, axis=1, norm="ortho")
    with_cp = np.concatenate((time[:, -cp_samples:], time), axis=1) if cp_samples else time
    with_cp *= np.exp(2j * np.pi * normalized_cfo * np.arange(with_cp.shape[1]) / n)
    noise = (rng.normal(size=with_cp.shape) + 1j * rng.normal(size=with_cp.shape)) / np.sqrt(2)
    received = np.fft.fft((with_cp + noise)[:, cp_samples:], axis=1, norm="ortho")
    pilot_csi = received[:pilot_symbols] / tx[:pilot_symbols]
    hhat = pilot_csi.mean(axis=0)
    equalized = received[pilot_symbols:] / hhat
    decisions_before = np.stack((equalized.real > 0, equalized.imag > 0), axis=-1)
    # Sensing reads a copy, leaving modem decisions and resources untouched.
    sensing_attenuation = -20 * np.log10(np.abs(pilot_csi.mean(axis=0) / h))
    decisions_after = np.stack((equalized.real > 0, equalized.imag > 0), axis=-1)
    errors = int(np.count_nonzero(decisions_before != (symbols[pilot_symbols:] > 0)))
    bits = decisions_before.size
    return dict(payload_bits=bits, bit_errors=errors, uncoded_ber=errors / bits,
                identical_decisions=bool(np.array_equal(decisions_before, decisions_after)),
                pilot_symbols=pilot_symbols, frame_symbols=frame_symbols, cp_samples=cp_samples,
                sensing_channels=len(sensing_attenuation), seed=seed, normalized_cfo=normalized_cfo,
                assumptions="Static LOS, ideal timing/common-phase tracking; no FEC or measured RF response")
