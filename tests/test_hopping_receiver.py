import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from thz_isac.hopping_receiver import (HoppingPlan, hamming_encode, hamming_decode,
    coded_payload, decode_payload, orbital_state, moving_ofdm_frame)


def test_schedule_charges_reference_retuning_prefix_and_frame_rounding():
    p = HoppingPlan(tuple(np.linspace(228., 316., 16)))
    c = p.counts(20.)
    assert c['transmission_total_s']+c['settling_total_s'] <= 20.
    assert 20.-c['transmission_total_s']-c['settling_total_s'] < 32*10000*p.symbol_duration_s
    assert c['payload']+c['pilots'] == c['total']
    assert len(p.frequency_ghz) == 256
    assert HoppingPlan(p.centers_ghz, settling_s=.01).counts(20.)['payload'] < c['payload']
    with pytest.raises(ValueError):
        HoppingPlan((200., 250.))
    with pytest.raises(ValueError):
        p.counts(.001)


def test_hamming_exhaustively_corrects_every_single_bit_error():
    inputs = np.array([[int(v) for v in f'{j:04b}'] for j in range(16)], np.uint8)
    coded = hamming_encode(inputs).reshape(16, 7)
    for bit in range(7):
        corrupted = coded.copy()
        corrupted[:, bit] ^= 1
        np.testing.assert_array_equal(hamming_decode(corrupted), inputs.ravel())


def test_crc_packet_framing_and_error_detection():
    bits, truth = coded_payload(np.random.default_rng(81), 10000)
    decoded = decode_payload(bits, truth)
    assert decoded['correct_packets'] == len(truth)
    corrupt = bits.copy()
    corrupt[:2] ^= 1
    result = decode_payload(corrupt, truth)
    assert result['crc_pass'] == len(truth)-1
    assert result['undetected_errors'] == 0


def test_orbit_velocity_matches_range_derivative():
    t = np.array([-60., -20., 0., 20., 60.])
    derivative = (orbital_state(t+.001)['range_m']-orbital_state(t-.001)['range_m'])/.002
    np.testing.assert_allclose(derivative, orbital_state(t)['radial_velocity_m_s'], atol=1e-5)
    assert orbital_state(0.)['elevation_deg'] == pytest.approx(90.)


def test_moving_fft_sync_and_payload_measurement():
    result = moving_ofdm_frame(np.full(16, 100.), center_ghz=280.,
        time_from_zenith_s=-65., seed=872, attenuation_db=np.full(16, .1),
        geometric_power_end_ratio=1.001)
    assert result['timing_correct']
    assert abs(result['actual_doppler_start_hz']) > 1e6
    assert result['post_correction_cfo_rms_hz'] < 3000
    assert result['valid'].all()
    assert abs(result['attenuation_estimate_db'].mean()-.1) < .01
    assert result['baseline']['correct_packets'] == result['baseline']['packets']
    assert result['decoded_outputs_equal']


def test_acquisition_limit_is_retained_as_a_failure_control():
    result = moving_ofdm_frame(np.full(16, 100.), center_ghz=280.,
        time_from_zenith_s=-65., seed=872, coarse_error_hz=700000.)
    # CP CFO is ambiguous modulo subcarrier spacing. A large initial orbit
    # prediction error cannot be silently declared synchronized.
    assert result['post_correction_cfo_rms_hz'] > 900000
    assert result['baseline']['correct_packets'] < result['baseline']['packets']//2
