"""Parallel Gaussian channel capacity with explicit pilot resource accounting.

This is a Shannon upper-bound model with known channel gains, not coded
throughput or a claim that the selected frequency windows are deployable.
"""
from dataclasses import dataclass
import numpy as np


def _gain_array(gain_per_watt):
    gain = np.asarray(gain_per_watt, dtype=float)
    if gain.ndim != 1 or not len(gain) or not np.isfinite(gain).all() or np.any(gain < 0):
        raise ValueError('Channel gain/noise ratios must be a finite nonnegative vector.')
    return gain


def waterfill_power(gain_per_watt, total_power_w):
    """Capacity-maximizing powers for equal-bandwidth independent channels."""
    gain = _gain_array(gain_per_watt)
    if not np.isfinite(total_power_w) or total_power_w <= 0:
        raise ValueError('Total power must be finite and positive.')
    active = np.flatnonzero(gain > 0)
    if not len(active):
        raise ValueError('At least one usable channel is required.')
    floor = 1 / gain[active]
    order = np.argsort(floor)
    sorted_floor = floor[order]
    # Remove the common minimum floor to avoid cancellation at low SNR.
    shifted = sorted_floor - sorted_floor[0]
    level = 0.0
    for k in range(1, len(active) + 1):
        level = (total_power_w + shifted[:k].sum()) / k
        if k == len(active) or level <= shifted[k]:
            break
    power = np.zeros_like(gain)
    power[active[order[:k]]] = np.maximum(level - shifted[:k], 0)
    # Enforce the budget against floating point summation drift.
    power *= total_power_w / power.sum()
    return power


def gaussian_rate_bps(gain_per_watt, power_w, bandwidth_per_channel_hz,
                      *, frame_symbols, pilot_symbols):
    """Return sum B log2(1+SNR) after explicitly removing pilot symbols."""
    gain = _gain_array(gain_per_watt)
    power = np.asarray(power_w, dtype=float)
    if power.shape != gain.shape or not np.isfinite(power).all() or np.any(power < 0):
        raise ValueError('Power must be a finite nonnegative vector matching the channels.')
    if not np.isfinite(bandwidth_per_channel_hz) or bandwidth_per_channel_hz <= 0:
        raise ValueError('Per-channel bandwidth must be positive.')
    for value in (frame_symbols, pilot_symbols):
        if isinstance(value, (bool, np.bool_)) or not np.isfinite(value) or int(value) != value:
            raise ValueError('Frame and pilot symbol counts must be integers.')
    if frame_symbols <= 0 or not 0 <= pilot_symbols < frame_symbols:
        raise ValueError('Pilot symbols must be between zero and the frame size minus one.')
    return float((1-pilot_symbols/frame_symbols)*bandwidth_per_channel_hz*
                 np.log1p(gain*power).sum()/np.log(2))


@dataclass(frozen=True)
class CapacityCheck:
    reference_bps: float
    candidate_bps: float
    relative_loss: float
    within_power_budget: bool
    accepted: bool


def check_capacity_contract(gain_per_watt, candidate_power_w, total_power_w,
                            bandwidth_per_channel_hz, *, frame_symbols,
                            baseline_pilot_symbols, candidate_pilot_symbols,
                            maximum_relative_loss=0.0, numerical_tolerance=1e-10):
    """Compare with communication-only waterfilling on the SAME channel.

    Zero loss is the default. Numerical tolerance is solely for arithmetic;
    it is not a policy allowance. Extra bands, power, or uncounted pilots must
    not enter either side of this comparison.
    """
    if not np.isfinite(maximum_relative_loss) or not 0 <= maximum_relative_loss < 1:
        raise ValueError('Maximum relative loss must lie in [0, 1).')
    if not np.isfinite(numerical_tolerance) or not 0 <= numerical_tolerance <= 1e-6:
        raise ValueError('Numerical tolerance must lie in [0, 1e-6].')
    baseline = waterfill_power(gain_per_watt, total_power_w)
    reference = gaussian_rate_bps(gain_per_watt, baseline, bandwidth_per_channel_hz,
                                  frame_symbols=frame_symbols, pilot_symbols=baseline_pilot_symbols)
    candidate = gaussian_rate_bps(gain_per_watt, candidate_power_w, bandwidth_per_channel_hz,
                                  frame_symbols=frame_symbols, pilot_symbols=candidate_pilot_symbols)
    power_ok = bool(np.sum(candidate_power_w) <= total_power_w*(1+numerical_tolerance))
    pilots_ok = candidate_pilot_symbols >= baseline_pilot_symbols
    loss = (reference-candidate)/reference
    return CapacityCheck(reference, candidate, float(loss), power_ok,
                         bool(power_ok and pilots_ok and loss <= maximum_relative_loss+numerical_tolerance))
