"""Raw coded OFDM bursts along the selected frequency hopping trajectory.

Bursts sample each hop at three locations. Only actually generated symbols
enter sensing variance and decoded throughput; no 20 s waveform is invented.
"""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.hopping_receiver import HoppingPlan, orbital_state, moving_ofdm_frame
from thz_isac.payload_sensing import attenuation_variance, resource_counts
from thz_isac.waveform_link import physical_channel_gain
from thz_isac.communication_capacity import waterfill_power
from thz_isac.attainable_estimation import efficient_linear_estimator
from receiver_design_physics import integrate_cached
from design_payload_receiver import OUT, config, write, Z


def main():
    plan = HoppingPlan(**json.loads((OUT/'hopping_plan.json').read_text())['plan'])
    cache = np.load(OUT/'standard_layers.npz')
    cfg = config(plan.spacing_hz)
    frame_s = plan.frame_symbols*plan.symbol_duration_s
    counts = plan.counts(20.)
    # Exact inverse of the ideal overhead geometry for the 45 degree center.
    from scipy.optimize import brentq
    center_time = brentq(lambda t: orbital_state(t)['elevation_deg']-45., -120., -1.)
    frames = []
    designs, backgrounds, variances = [], [], []
    for hop, center in enumerate(plan.centers_ghz):
        sl = slice(hop*16, (hop+1)*16)
        local_designs, local_background, local_variance = [], [], []
        for burst, offset in enumerate([.02, .30, .58]):
            t = center_time-5+hop*.625+plan.settling_s+offset
            elevation = float(orbital_state(t+frame_s/2)['elevation_deg'])
            a = integrate_cached(cache, 'standard', elevation)
            f = a['frequency_ghz'][sl]
            gain = physical_channel_gain(f, a['background_db'][sl], a['sky_temperature_k'][sl], cfg, elevation)['gain_per_watt']
            power = waterfill_power(gain, 10**((cfg.tx_power_dbm-30)/10))
            snr = gain*power
            d = np.column_stack([a['gas'][sl, :3], a['pm'][sl]])
            n = np.column_stack([a['background_db'][sl], a['gas'][sl, 3:]])
            # Known geometry normalization. Atmospheric gain is locally
            # constant inside a 10.625 ms burst; variation between bursts is
            # recomputed from exact refracted paths and thermal transfer.
            ratio = float((orbital_state(t)['range_m']/orbital_state(t+frame_s)['range_m'])**2)
            frames.append(dict(hop=hop, burst=burst, time=t, elevation=elevation,
                               center=center, snr=snr, design=d, ratio=ratio))
            local_designs.append(d)
            local_background.append(n)
            local_variance.append(2*attenuation_variance(snr, plan.frame_symbols-plan.pilot_symbols, 'm2m4'))
        designs.append(np.mean(local_designs, axis=0))
        backgrounds.append(np.mean(local_background, axis=0))
        variances.append(np.sum(local_variance, axis=0)/9)
    d = np.concatenate(designs)
    f = plan.frequency_ghz
    n = np.column_stack([np.ones(len(f)), np.concatenate(backgrounds), (f-f.mean())/np.ptp(f)])
    corr = np.exp(-abs(f[:, None]-f[None, :])/10)
    covariance = np.diag(np.concatenate(variances))+.001**2*corr
    estimator = efficient_linear_estimator(d, n, covariance)
    h = estimator.operator
    sd = np.sqrt(np.diag(h@covariance@h.T))
    concentration = (Z+norm.ppf(.95))*sd[2]
    write('moving_protocol.json', dict(seed=2026092902, frames_per_hop_per_pass=3,
        waveform='IFFT, cyclic prefix, AWGN, exact orbital carrier Doppler, integer timing acquisition, CP CFO estimate, existing pilot phase tracking, Hamming (7,4) and CRC16.',
        acquisition='Initial predicted Doppler error 100 kHz; timing unknown within nine samples. Failure control at 700 kHz exceeds CP unambiguous range.',
        time='Three 10.625 ms bursts per hop spread over a 10 second pass; matched independent reference pass. Only generated bursts count as sensing data. Waiting between orbital passes excluded.',
        gain='Known geometric range normalization; atmospheric gain frozen within each 10.625 ms burst and recomputed between bursts. Sample and reference have matched weather. Differential calibration is uncorrected 0.001 dB random correlated residual, held fixed across bursts.',
        alternative_ch3cn_ug_m3=float(concentration), simulated_transmission_s=2*48*frame_s,
        statistical_scope='Two raw trajectory controls, not an empirical recall estimate; 10000-draw nonzero calibration assessment is separate.',
        limitations=['Narrowband Doppler per 16 MHz hop; wideband time dilation, fractional timing, sample clock error, multipath and measured phase noise are not simulated.', 'Hardware real time execution and full acquisition are not demonstrated. CP and pilot processing buffers the entire 10.625 ms frame.']))
    rng = np.random.default_rng(2026092902)
    rows, cases, saved = [], [], dict(design=d, nuisance=n, covariance=covariance, operator=h, sd=sd)
    for case, value in [('blank', 0.), ('CH3CN_local_limit', concentration)]:
        residual = .001*np.linalg.cholesky(corr)@rng.normal(size=len(f))
        signals = {key: np.zeros((16, 3, 16)) for key in ['reference', 'sample']}
        for frame in frames:
            hop, burst = frame['hop'], frame['burst']
            sl = slice(hop*16, (hop+1)*16)
            for pass_id, key in enumerate(['reference', 'sample']):
                attenuation = np.zeros(16) if key == 'reference' else frame['design'][:, 2]*value+residual[sl]
                result = moving_ofdm_frame(frame['snr'], center_ghz=frame['center'],
                    time_from_zenith_s=frame['time'], seed=int(rng.integers(1, 2**31)),
                    attenuation_db=attenuation, geometric_power_end_ratio=frame['ratio'])
                if not result['valid'].all():
                    raise RuntimeError('Invalid moving M2M4 inversion')
                signals[key][hop, burst] = result['attenuation_estimate_db']
                row = dict(case=case, pass_kind=key, hop=hop, burst=burst,
                    time_from_zenith_s=frame['time'], elevation_deg=frame['elevation'],
                    center_ghz=frame['center'], minimum_snr_db=float(10*np.log10(min(frame['snr']))),
                    **{k: result[k] for k in ['timing_correct', 'post_correction_cfo_rms_hz', 'actual_doppler_start_hz',
                        'actual_doppler_end_hz', 'uncoded_bit_errors', 'coded_bits', 'frame_duration_s', 'decoded_outputs_equal']},
                    **result['baseline'])
                rows.append(row)
            if burst == 2:
                print(case, 'hop', hop+1, '/16 decoded', flush=True)
        observation = (signals['sample']-signals['reference']).mean(axis=1).ravel()
        estimate = h@observation
        truth = np.array([0., 0., value, 0., 0.])
        saved[case+'_observation'] = observation
        saved[case+'_calibration_residual'] = residual
        saved[case+'_truth'] = truth
        cases.append(dict(case=case, truth_ug_m3=truth.tolist(), estimated_ug_m3=estimate.tolist(),
            standardized_error=((estimate-truth)/sd).tolist(),
            gas_detections=(estimate[:3] > Z*sd[:3]).tolist()))
    # Out-of-acquisition-range failure is recorded, not removed from results.
    failure = moving_ofdm_frame(frames[0]['snr'], center_ghz=frames[0]['center'],
        time_from_zenith_s=frames[0]['time'], seed=42, coarse_error_hz=700000.)
    table = pd.DataFrame(rows)
    table.to_csv(OUT/'moving_waveform_frames.csv', index=False)
    np.savez_compressed(OUT/'moving_waveform_replay.npz', **saved)
    stationary = resource_counts(20., symbol_duration_s=plan.symbol_duration_s)
    transmission_fraction = counts['transmission_total_s']/20
    schedule_loss = 1-(2*16*counts['payload'])/stationary['payload']
    summary = dict(status='passed' if table.timing_correct.all() and table.decoded_outputs_equal.all() else 'failed',
        generated_frames=len(table), raw_complex_samples=int(len(table)*10000*17),
        coded_information_bits=int(table.information_bits.sum()),
        correct_packets=int(table.correct_packets.sum()), packets=int(table.packets.sum()),
        information_bit_errors=int(table.information_bit_errors.sum()),
        undetected_crc_errors=int(table.undetected_errors.sum()),
        observed_correct_payload_bps=float(table.correct_packets.sum()*512/table.frame_duration_s.sum()),
        receiver_frame_buffer_latency_ms=1000*frame_s,
        measured_incremental_sensing_packet_loss=0 if table.decoded_outputs_equal.all() else None,
        scheduling_loss_vs_fixed_band_pct=float(100*schedule_loss),
        scheduling_comparison='Same code, QPSK, 16 MHz and 23 dBm. Resource loss from retuning and whole frames; not Shannon capacity or measured hardware throughput.',
        maximum_residual_cfo_rms_hz=float(table.post_correction_cfo_rms_hz.max()),
        maximum_absolute_doppler_hz=float(abs(table.actual_doppler_start_hz).max()),
        cases=cases,
        failed_acquisition_control=dict(coarse_error_hz=700000.,
            post_correction_cfo_rms_hz=failure['post_correction_cfo_rms_hz'], **failure['baseline']),
        calibration_residual_std_db=.001, hardware_validated=False)
    write('moving_waveform_summary.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
