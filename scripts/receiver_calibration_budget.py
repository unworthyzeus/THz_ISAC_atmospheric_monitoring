"""Invert the receiver design into measurable calibration requirements."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.payload_sensing import draw_attenuation
from design_payload_receiver import OUT, fit, Z, write
from evaluate_receiver_design import sliced


def main():
    plan = HoppingPlan(**json.loads((OUT/'hopping_plan.json').read_text())['plan'])
    data = sliced(OUT/'standard_45_physics.npz')
    rows = []
    for duration in [20., 100.]:
        for j, target in enumerate(['H2CO', 'CH3OH', 'CH3CN']):
            for concentration in [1., 5., 10.]:
                def margin(sigma):
                    return concentration-(Z+norm.ppf(.95))*fit(data, plan, total_s=duration, residual_db=sigma)['sd'][j]
                thermal = margin(0.)
                if thermal <= 0:
                    sigma = np.nan
                    status = 'thermal information already insufficient'
                else:
                    sigma = brentq(margin, 0., .1, xtol=1e-12)
                    status = 'conditional residual requirement, not measured capability'
                nominal = fit(data, plan, total_s=duration, residual_db=0.)
                allowance = max(thermal, 0)/(2*np.abs(nominal['operator'][j]).sum())
                rows.append(dict(target=target, concentration_ug_m3=concentration, total_s=duration,
                    required_max_correlated_residual_std_db=sigma,
                    maximum_arbitrary_per_tone_bias_db=allowance if thermal > 0 else np.nan,
                    random_budget_model='10 GHz exponential correlation; 95% local power; family alpha 1% over six outputs',
                    deterministic_budget_model='Separate zero random residual calculation; robust null threshold, adverse alternative bias, fixed zero-residual operator. Do not combine these two separate budgets without recomputation.',
                    status=status))
    pd.DataFrame(rows).to_csv(OUT/'calibration_acceptance_budget.csv', index=False)
    # Frequency-specific calibration acquisition template, deliberately empty.
    pd.DataFrame(columns=['campaign_id', 'observation_id', 'time', 'frequency_ghz',
        'error_db', 'reference_id', 'receiver_id', 'temperature_k', 'hop_settling_s']).to_csv(OUT/'calibration_measurement_template.csv', index=False)
    pd.DataFrame(dict(hop=np.repeat(np.arange(16), 16), frequency_ghz=plan.frequency_ghz)).to_csv(OUT/'required_calibration_frequencies.csv', index=False)
    # Settling is not free; all cases use complete frames and both passes.
    settling = []
    for seconds in [.0001, .001, .01, .1]:
        p = HoppingPlan(plan.centers_ghz, settling_s=seconds)
        r = fit(data, p, residual_db=.001)
        settling.append(dict(settling_per_hop_s=seconds, **r['count'],
            ch3cn_local_lod95_ug_m3=(Z+norm.ppf(.95))*r['sd'][2]))
    pd.DataFrame(settling).to_csv(OUT/'settling_sensitivity.csv', index=False)
    write('calibration_measurement_gate.json', dict(status='awaiting real measurements',
        empty_template=True,
        requirements=['Record repeated independent full sweeps at the intended power, timing, frequencies and temperature range.',
            'error_db must be measured differential sample/reference error after a known physical calibration standard, including gain normalization.',
            'Do not derive calibration truth from the gas retrieval being assessed.',
            'Fit correction/covariance on separate campaigns, freeze it, then evaluate subsequent campaigns.',
            'Check persistent signed drift separately from zero-mean covariance; a random standard deviation is not a systematic bound.',
            'Verify covariance and detection performance on separate transmissions with independent concentration truth.'],
        existing_analysis_command='python scripts/characterize_receiver_calibration.py INPUT.csv --output results/receiver_measured_calibration --degree 1',
        existing_analysis_scope='Descriptive repeated-sweep analysis only; it does not itself certify detection power or independence.',
        failure_policy='Missing measurements remain missing. No fabricated observations or positive field claim.'))
    rng = np.random.default_rng(2026092903)
    response_rows = []
    for duration, sigma in [(20., .001), (100., .001), (100., .0001), (20., .0001)]:
        r = fit(data, plan, total_s=duration, residual_db=sigma)
        snr, d, h = r['snr'][r['mask']], r['design'], r['operator']
        count = r['count']['payload']
        factor = sigma*np.linalg.cholesky(r['correlation'])
        saved = dict(operator=h, sd=r['sd'], design=d, count=count, sigma=sigma, snr=snr)
        for label, concentration in [('null', 0.), ('one_ug', 1.)]:
            batches = []
            for _ in range(20):
                sample, valid = draw_attenuation(rng, d[:, 2]*concentration, snr, count, 500, 'm2m4')
                ref, valid_ref = draw_attenuation(rng, np.zeros(len(snr)), snr, count, 500, 'm2m4')
                if not valid.all() or not valid_ref.all():
                    raise RuntimeError('Invalid response estimate')
                batches.append((sample-ref+rng.normal(size=sample.shape)@factor.T)@h.T)
            saved[label] = np.concatenate(batches)
        hits = int(np.sum(saved['one_ug'][:, 2] > Z*r['sd'][2]))
        false = int(np.any(saved['null'] > Z*r['sd'], axis=1).sum())
        from scipy.stats import binomtest
        ci = binomtest(hits, 10000).proportion_ci()
        response_rows.append(dict(total_s=duration, residual_std_db=sigma, trials=10000,
            target='CH3CN', concentration_ug_m3=1., hits=hits, recall_pct=hits/100,
            ci95_lower_pct=100*ci.low, ci95_upper_pct=100*ci.high,
            family_false_count=false, family_false_alarm_pct=false/100,
            calibration_status='Assumed random residual covariance; not measured calibration'))
        np.savez_compressed(OUT/f'calibration_response_{int(duration)}_{sigma:g}.npz', **saved)
    pd.DataFrame(response_rows).to_csv(OUT/'calibration_response_controls.csv', index=False)
    print(pd.DataFrame(rows)[['target', 'concentration_ug_m3', 'total_s', 'required_max_correlated_residual_std_db', 'maximum_arbitrary_per_tone_bias_db']].to_string(index=False))
    print(pd.DataFrame(response_rows).to_string(index=False))


if __name__ == '__main__':
    main()
