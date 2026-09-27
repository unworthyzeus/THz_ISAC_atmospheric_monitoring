"""A sequential, one active RF chain OFDM sensing schedule."""
from dataclasses import dataclass
import numpy as np
from .payload_sensing import resource_counts
from .payload_sensing import moment_power
import binascii


@dataclass(frozen=True)
class HoppingPlan:
    centers_ghz: tuple
    subcarriers_per_block: int = 16
    spacing_hz: float = 1e6
    cyclic_prefix_fraction: float = 1/16
    frame_symbols: int = 10000
    pilot_symbols: int = 30
    settling_s: float = .001

    def __post_init__(self):
        n = self.subcarriers_per_block
        c = np.asarray(self.centers_ghz, float)
        if c.ndim != 1 or not len(c) or not np.isfinite(c).all() or np.any(np.diff(c) <= 0):
            raise ValueError('Strictly ordered finite centers required')
        if isinstance(n, bool) or int(n) != n or n < 16 or n & (n-1):
            raise ValueError('FFT length must be a power of two, at least 16')
        if not np.isfinite([self.spacing_hz, self.settling_s, self.cyclic_prefix_fraction]).all() or self.spacing_hz <= 0 or self.settling_s < 0:
            raise ValueError('Invalid spacing or settling time')
        if not 0 < self.cyclic_prefix_fraction < 1 or int(n*self.cyclic_prefix_fraction) != n*self.cyclic_prefix_fraction:
            raise ValueError('Integer nonzero cyclic prefix required')
        if not 0 < self.pilot_symbols < self.frame_symbols:
            raise ValueError('Invalid pilot schedule')
        half = n*self.spacing_hz/2e9
        if c[0]-half < 220 or c[-1]+half > 330 or np.any(np.diff(c) < 2*half):
            raise ValueError('Nonoverlapping blocks must fit WR3.4 band')

    @property
    def frequency_ghz(self):
        offsets = (np.arange(self.subcarriers_per_block)-(self.subcarriers_per_block-1)/2)*self.spacing_hz/1e9
        return np.concatenate([c+offsets for c in self.centers_ghz])

    @property
    def symbol_duration_s(self):
        return (1+self.cyclic_prefix_fraction)/self.spacing_hz

    def counts(self, total_reference_and_sample_s):
        dwell = total_reference_and_sample_s/2/len(self.centers_ghz)-self.settling_s
        count = resource_counts(dwell, symbol_duration_s=self.symbol_duration_s,
                                frame_symbols=self.frame_symbols, pilot_symbols=self.pilot_symbols)
        count['settling_total_s'] = 2*len(self.centers_ghz)*self.settling_s
        count['transmission_total_s'] = 2*len(self.centers_ghz)*count['charged_duration_s']
        count['wall_total_s'] = total_reference_and_sample_s
        return count

    def net_rate_bps(self, gain, power, total_s=20.):
        # Gaussian-input information benchmark, NOT QPSK modem throughput.
        count = self.counts(total_s)
        return float(2*count['payload']*np.log2(1+gain*power).sum()/total_s)


def orbital_state(time_from_zenith_s, altitude_m=550000., earth_m=6371000.):
    t = np.asarray(time_from_zenith_s, float)
    r = earth_m+altitude_m
    omega = np.sqrt(3.986004418e14/r**3)
    angle = omega*t
    distance = np.sqrt(r*r+earth_m*earth_m-2*r*earth_m*np.cos(angle))
    elevation = np.rad2deg(np.arcsin((r*np.cos(angle)-earth_m)/distance))
    velocity = earth_m*r*omega*np.sin(angle)/distance
    return dict(range_m=distance, elevation_deg=elevation, radial_velocity_m_s=velocity)


def hamming_encode(bits):
    """Systematic Hamming (7,4), even parity; an explicit simple FEC control."""
    b = np.asarray(bits, np.uint8).reshape(-1, 4)
    c = np.zeros((len(b), 7), np.uint8)
    c[:, [2, 4, 5, 6]] = b
    c[:, 0] = b[:, 0] ^ b[:, 1] ^ b[:, 3]
    c[:, 1] = b[:, 0] ^ b[:, 2] ^ b[:, 3]
    c[:, 3] = b[:, 1] ^ b[:, 2] ^ b[:, 3]
    return c.ravel()


def hamming_decode(bits):
    c = np.asarray(bits, np.uint8).reshape(-1, 7).copy()
    syndrome = (c[:, 0] ^ c[:, 2] ^ c[:, 4] ^ c[:, 6]).astype(int)
    syndrome += 2*(c[:, 1] ^ c[:, 2] ^ c[:, 5] ^ c[:, 6])
    syndrome += 4*(c[:, 3] ^ c[:, 4] ^ c[:, 5] ^ c[:, 6])
    rows = np.flatnonzero(syndrome)
    c[rows, syndrome[rows]-1] ^= 1
    return c[:, [2, 4, 5, 6]].ravel()


def coded_payload(rng, bit_count):
    """512 information bits + CRC16, followed by Hamming coding, per packet."""
    encoded_packet_bits = 528//4*7
    packets = bit_count//encoded_packet_bits
    information = rng.integers(0, 256, size=(packets, 64), dtype=np.uint8)
    framed = np.zeros((packets, 66), np.uint8)
    framed[:, :64] = information
    for j, row in enumerate(information):
        crc = binascii.crc_hqx(row.tobytes(), 0xffff)
        framed[j, -2:] = [crc >> 8, crc & 255]
    encoded = hamming_encode(np.unpackbits(framed))
    output = np.r_[encoded, np.zeros(bit_count-len(encoded), np.uint8)]
    return output, information


def decode_payload(bits, information):
    count = len(information)*924
    received = np.packbits(hamming_decode(bits[:count])).reshape(-1, 66)
    crc_ok = np.array([binascii.crc_hqx(row[:64].tobytes(), 0xffff) ==
                      (int(row[-2])*256+int(row[-1])) for row in received])
    correct = np.all(received[:, :64] == information, axis=1)
    return dict(packets=len(information), crc_pass=int(crc_ok.sum()),
        correct_packets=int((correct & crc_ok).sum()), undetected_errors=int((~correct & crc_ok).sum()),
        information_bit_errors=int(np.unpackbits(received[:, :64] ^ information).sum()),
        information_bits=int(information.size*8))


def moving_ofdm_frame(snr, *, center_ghz, time_from_zenith_s, seed,
                      attenuation_db=None, spacing_hz=1e6, frame_symbols=10000,
                      pilot_symbols=30, coarse_error_hz=100000., timing_offset=3,
                      geometric_power_end_ratio=1.):
    """Raw IFFT/CP channel and blind CP synchronization with pilot phase tracking.

    Orbit feedforward removes predicted carrier Doppler with a deliberately
    erroneous initial frequency. Timing and remaining CFO are estimated from
    received CP samples; phase/channel estimates use existing pilots. Sensing
    sees geometry-normalized FFT magnitudes BEFORE pilot amplitude equalization.
    The supplied gain trajectory is known geometry, not an estimated calibration.
    """
    sn = np.asarray(snr, float)
    n, cp = len(sn), len(sn)//16
    if n < 16 or n & (n-1) or np.any(sn <= 0) or not np.isfinite(sn).all():
        raise ValueError('Power-of-two FFT and positive finite SNR required')
    if not 0 < pilot_symbols < frame_symbols or not 0 <= timing_offset <= 8:
        raise ValueError('Invalid frame parameters')
    if geometric_power_end_ratio <= 0:
        raise ValueError('Positive geometric power ratio required')
    a = np.zeros(n) if attenuation_db is None else np.broadcast_to(attenuation_db, (n,))
    rng = np.random.default_rng(seed)
    pilots = np.unique(np.linspace(0, frame_symbols-1, pilot_symbols, dtype=int))
    payload = np.setdiff1d(np.arange(frame_symbols), pilots)
    bits, information = coded_payload(rng, len(payload)*n*2)
    x = np.empty((frame_symbols, n), complex)
    qbits = bits.reshape(len(payload), n, 2)
    x[payload] = ((1-2*qbits[:, :, 0].astype(float))+1j*(1-2*qbits[:, :, 1].astype(float)))/np.sqrt(2)
    pb = rng.integers(0, 2, (len(pilots), n, 2))
    x[pilots] = ((1-2*pb[:, :, 0])+1j*(1-2*pb[:, :, 1]))/np.sqrt(2)
    gain = np.linspace(1., geometric_power_end_ratio, frame_symbols)
    signal = x*np.sqrt(sn*10**(-a/10))[None, :]*np.sqrt(gain[:, None])
    # Physical frequency vectors are sorted. Convert to FFT bin order, using
    # the half-bin carrier shift implied by an even, symmetric tone grid.
    waveform = np.fft.ifft(np.fft.ifftshift(signal, axes=1), axis=1, norm='ortho')
    waveform = np.concatenate([waveform[:, -cp:], waveform], axis=1).ravel()
    sample_rate = n*spacing_hz
    t = np.arange(len(waveform))/sample_rate
    state = orbital_state(time_from_zenith_s+t)
    # Integrate the exact analytic radial velocity, avoiding range subtraction
    # cancellation in carrier phase at subnanosecond sample intervals.
    from scipy.constants import speed_of_light
    fft_carrier_hz = center_ghz*1e9+spacing_hz/2
    doppler = -fft_carrier_hz*state['radial_velocity_m_s']/speed_of_light
    phase = 2*np.pi*np.cumsum(doppler)/sample_rate+.37
    pred = float(doppler[0])+coarse_error_hz
    received = waveform*np.exp(1j*phase)
    received += (rng.normal(size=len(t))+1j*rng.normal(size=len(t)))/np.sqrt(2)
    # A rough acquisition window is assumed. Integer timing within that
    # window is unknown; fractional timing and a full search remain separate.
    padding = (rng.normal(size=16)+1j*rng.normal(size=16))/np.sqrt(2)
    received = np.r_[padding[:timing_offset], received, padding]
    received *= np.exp(-2j*np.pi*pred*(np.arange(len(received))-timing_offset)/sample_rate)
    metrics = []
    for shift in range(9):
        frame = received[shift:shift+frame_symbols*(n+cp)].reshape(frame_symbols, n+cp)
        left, right = frame[:, :cp], frame[:, n:n+cp]
        corr = np.sum(np.conj(left)*right)
        metrics.append(abs(corr)**2/(np.sum(abs(left)**2)*np.sum(abs(right)**2)))
    timing = int(np.argmax(metrics))
    frame = received[timing:timing+frame_symbols*(n+cp)].reshape(frame_symbols, n+cp)
    corr = np.sum(np.conj(frame[:, :cp])*frame[:, n:n+cp])
    estimated_cfo = np.angle(corr)*spacing_hz/(2*np.pi)
    frame *= np.exp(-2j*np.pi*estimated_cfo*np.arange(frame.size).reshape(frame.shape)/sample_rate)
    y = np.fft.fftshift(np.fft.fft(frame[:, cp:], axis=1, norm='ortho'), axes=1)/np.sqrt(gain[:, None])
    def communication_decode(received_fft):
        phase_estimate = np.unwrap(np.angle(np.sum(received_fft[pilots]*np.conj(x[pilots]), axis=1)))
        tracked = received_fft*np.exp(-1j*np.interp(np.arange(frame_symbols), pilots, phase_estimate))[:, None]
        channel = np.mean(tracked[pilots]/x[pilots], axis=0)
        equalized = tracked[payload]/channel
        decisions = np.stack([equalized.real < 0, equalized.imag < 0], axis=-1).astype(np.uint8).ravel()
        return decisions, decode_payload(decisions, information)
    # Run the baseline BEFORE the sensing consumer. Decode again afterwards
    # so accidental in-place modification would be visible in actual bits.
    baseline_bits, baseline = communication_decode(y.copy())
    # Magnitudes are invariant to common phase, but not ICI. Residual ICI
    # remains in this observable and is measured against the physical truth.
    powers = abs(y[payload])**2
    s, v, valid = moment_power(powers.mean(0), (powers**2).mean(0), len(payload))
    decoded_bits, sensed = communication_decode(y)
    return dict(signal=s, noise=v, valid=valid, payload_symbols=len(payload),
        attenuation_estimate_db=-10*np.log10(s/sn),
        estimated_timing_samples=timing, true_timing_samples=timing_offset,
        timing_correct=bool(timing == timing_offset), estimated_residual_cfo_hz=float(estimated_cfo),
        post_correction_cfo_rms_hz=float(np.sqrt(np.mean((doppler-pred-estimated_cfo)**2))),
        actual_doppler_start_hz=float(doppler[0]), actual_doppler_end_hz=float(doppler[-1]),
        uncoded_bit_errors=int(np.count_nonzero(decoded_bits != bits)), coded_bits=len(bits),
        frame_duration_s=frame_symbols*(n+cp)/sample_rate,
        baseline=baseline, with_sensing=sensed,
        decoded_outputs_equal=bool(np.array_equal(baseline_bits, decoded_bits) and baseline == sensed),
        minimum_timing_metric=float(min(metrics)), winning_timing_metric=float(max(metrics)))
