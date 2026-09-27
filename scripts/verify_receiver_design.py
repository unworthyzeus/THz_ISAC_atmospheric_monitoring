"""Independent replay of resource, numerical and communication evidence."""
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import norm, binomtest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.payload_sensing import attenuation_variance
from thz_isac.hopping_receiver import HoppingPlan

OUT = ROOT/'results/receiver_design'


def main():
    checks, failures = [], []
    def check(condition, label):
        checks.append(label)
        if not condition:
            failures.append(label)
    p = HoppingPlan(**json.loads((OUT/'hopping_plan.json').read_text())['plan'])
    physics = json.loads((OUT/'physics_manifest.json').read_text())
    for name, digest in physics['inputs'].items():
        check(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, 'physical input '+name)
    for name, digest in physics['outputs'].items():
        check(hashlib.sha256((OUT/name).read_bytes()).hexdigest() == digest, 'physical output '+name)
        if name.endswith('_physics.npz'):
            check(np.array_equal(np.load(OUT/name)['frequency_ghz'][:256], p.frequency_ghz), 'exact receiver frequency grid '+name)
    check(len([n for n in physics['outputs'] if n.endswith('_physics.npz')]) == 20, 'all 20 physical cases present')
    resources = pd.read_csv(OUT/'resources.csv')
    for i, row in resources.iterrows():
        check(row.transmission_total_s+row.settling_total_s <= row.wall_total_s, 'wall time '+str(i))
        check(np.isclose(row.energy_j, row.peak_radiated_power_w*row.transmission_total_s), 'energy '+str(i))
        check(row.peak_radiated_power_w <= 10**((23-30)/10)*(1+1e-12), 'one active chain power '+str(i))
        check(row.payload+row.pilots == row.total, 'symbols '+str(i))
        check(np.isclose(row.total*p.symbol_duration_s*32, row.transmission_total_s, rtol=1e-12), 'CP and reference '+str(i))
    z = norm.isf(.01/6)
    a = np.load(OUT/'nonzero_calibration_validation.npz')
    h, sd, d, n, c = (a[k] for k in ['operator', 'sd', 'design', 'nuisance', 'covariance'])
    scales = np.linalg.norm(d, axis=0)
    error = (h[:5]@d-np.eye(5))*scales[:, None]/scales[None, :]
    check(np.max(abs(error)) < 1e-5, 'scaled joint identity')
    check(np.max(abs(h@n)/(sd[:, None]*np.linalg.norm(n, axis=0))) < 1e-7, 'nuisance annihilation')
    check(np.allclose(sd**2, np.diag(h@c@h.T), rtol=1e-9), 'covariance propagation')
    thermal = 2*attenuation_variance(a['snr'], int(a['count']), 'm2m4')
    check(np.allclose(c, np.diag(thermal)+a['residual_cholesky']@a['residual_cholesky'].T, rtol=1e-10, atol=1e-16), 'nonzero calibration added once')
    null = a['null']
    family = int(np.any(null > z*sd, axis=1).sum())
    check(binomtest(family, len(null), .01, alternative='greater').pvalue > .01/5, 'family false alarm')
    validation = pd.read_csv(OUT/'nonzero_calibration_validation.csv')
    for j, row in validation.iterrows():
        positive = a[row.target]
        hits = int((positive[:, j] > z*sd[j]).sum())
        check(hits == row.hits, 'power replay '+row.target)
        check(family == row.family_false_count, 'family replay '+row.target)
        check(abs(hits/len(positive)-.95) <= 5*np.sqrt(.95*.05/len(positive))+.002, '95 percent power '+row.target)
        check(abs(null[:, j].mean()) < 5*sd[j]/np.sqrt(len(null)), 'null bias '+row.target)
        check(abs(null[:, j].var(ddof=1)/sd[j]**2-1) < .07, 'variance '+row.target)
        check(row.maximum_absorption_at_limit_db < 1., 'trace domain '+row.target)
    responses = pd.read_csv(OUT/'calibration_response_controls.csv')
    for i, row in responses.iterrows():
        saved = np.load(OUT/f'calibration_response_{int(row.total_s)}_{row.residual_std_db:g}.npz')
        hits = int((saved['one_ug'][:, 2] > z*saved['sd'][2]).sum())
        false = int(np.any(saved['null'] > z*saved['sd'], axis=1).sum())
        check(hits == row.hits and false == row.family_false_count, 'calibration response replay '+str(i))
        check(binomtest(false, row.trials, .01, alternative='greater').pvalue > .01/5, 'calibration family false alarm '+str(i))
        ci = binomtest(hits, row.trials).proportion_ci()
        check(np.isclose(ci.low*100, row.ci95_lower_pct) and np.isclose(ci.high*100, row.ci95_upper_pct), 'exact interval '+str(i))
    frames = pd.read_csv(OUT/'moving_waveform_frames.csv')
    moving = json.loads((OUT/'moving_waveform_summary.json').read_text())
    check(len(frames) == 192 and frames.timing_correct.all(), 'all raw frames acquired')
    check(frames.decoded_outputs_equal.all(), 'passive observation preserves decoded output')
    check(frames.correct_packets.sum() == moving['correct_packets'], 'coded packet replay')
    check(frames.undetected_errors.sum() == moving['undetected_crc_errors'], 'CRC errors retained')
    check(np.isclose(frames.post_correction_cfo_rms_hz.max(), moving['maximum_residual_cfo_rms_hz']), 'CFO replay')
    check(moving['failed_acquisition_control']['correct_packets'] == 0, 'acquisition failure retained')
    check(moving['scheduling_loss_vs_fixed_band_pct'] > 0, 'retuning not falsely free')
    replay = np.load(OUT/'moving_waveform_replay.npz')
    for case in moving['cases']:
        estimate = replay['operator']@replay[case['case']+'_observation']
        check(np.allclose(estimate, case['estimated_ug_m3']), 'moving sensing replay '+case['case'])
        check(np.max(abs((estimate-replay[case['case']+'_truth'])/replay['sd'])) < 5, 'raw response sanity '+case['case'])
    check(pd.read_csv(OUT/'calibration_measurement_template.csv').empty, 'no manufactured measurements')
    engineering = json.loads((OUT/'engineering_controls.json').read_text())
    check(next(r for r in engineering if r['case'] == 'unamplified_converter_before_backoff')['status'] == 'rejected', 'converter rejection retained')
    check(next(r for r in engineering if r['case'] == 'contiguous_exact_spectrum')['status'] == 'rejected', 'contiguous rank failure retained')
    result = dict(status='passed' if not failures else 'failed', checks=len(checks), failures=failures,
        scope='Numerical replay and conditional receiver controls. Calibration covariance and hardware performance are not measured.')
    (OUT/'verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))
    if failures:
        raise RuntimeError('Receiver verification failed')


if __name__ == '__main__':
    main()
