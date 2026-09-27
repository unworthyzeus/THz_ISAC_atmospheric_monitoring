"""Frozen candidate evaluation with nonzero residual and retained failures."""
from pathlib import Path
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, binomtest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.payload_sensing import draw_attenuation, attenuation_variance
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.waveform_link import OFDMPlan
from thz_isac.attainable_estimation import efficient_linear_estimator
from design_payload_receiver import OUT, fit, write, sha, Z
from run_payload_bounds import corrected_floor

TARGETS = ['H2CO', 'CH3OH', 'CH3CN', 'PM2.5', 'PMcoarse', 'PM10']


def sliced(path, hopping=True):
    a = np.load(path)
    sl = slice(0, 256) if hopping else slice(256, 512)
    return {k: (a[k][sl] if a[k].ndim else a[k]) for k in a.files}


def validation(data, plan):
    # Thresholds and design depend on analytic model only. New random seed.
    sigma, draws = .001, 10000
    r = fit(data, plan, residual_db=sigma)
    h, sd, d = r['operator'], r['sd'], r['design']
    snr, count = r['snr'][r['mask']], r['count']['payload']
    rcov = sigma**2*r['correlation']
    floors = [corrected_floor(h, sd, d, j, snr, count, 'm2m4', rcov) for j in range(3)]
    rng = np.random.default_rng(2026092901)
    chol = np.linalg.cholesky(rcov)
    saved = dict(operator=h, sd=sd, design=d, nuisance=r['nuisance'], covariance=r['covariance'],
        floors=floors, count=count, snr=snr, residual_cholesky=chol)
    rows = []
    for j in [-1, 0, 1, 2]:
        signal = np.zeros(len(snr)) if j == -1 else d[:, j]*floors[j]
        scores = []
        for start in range(0, draws, 500):
            sample, valid = draw_attenuation(rng, signal, snr, count, 500, 'm2m4')
            reference, refvalid = draw_attenuation(rng, np.zeros(len(snr)), snr, count, 500, 'm2m4')
            if not valid.all() or not refvalid.all():
                raise RuntimeError('Invalid moment inversion retained as validation failure')
            # Persistent residual is drawn ONCE per independent acquisition,
            # never once per symbol or averaged away with the thermal noise.
            residual = rng.normal(size=sample.shape) @ chol.T
            scores.append((sample-reference+residual) @ h.T)
        scores = np.concatenate(scores)
        saved['null' if j == -1 else TARGETS[j]] = scores
        if j == -1:
            null = scores
            family = int(np.any(null > Z*sd, axis=1).sum())
        else:
            hits = int((scores[:, j] > Z*sd[j]).sum())
            ci = binomtest(hits, draws).proportion_ci()
            rows.append(dict(target=TARGETS[j], draws=draws, residual_std_db=sigma,
                response_lod95_ug_m3=floors[j], maximum_absorption_at_limit_db=float(max(signal)),
                hits=hits, recall_pct=100*hits/draws, ci_lower_pct=100*ci.low, ci_upper_pct=100*ci.high,
                false_count=int((null[:, j] > Z*sd[j]).sum()), family_false_count=family,
                passed=bool(abs(hits/draws-.95) <= 5*np.sqrt(.95*.05/draws)+.002)))
    np.savez_compressed(OUT/'nonzero_calibration_validation.npz', **saved)
    pd.DataFrame(rows).to_csv(OUT/'nonzero_calibration_validation.csv', index=False)
    return rows


def main():
    plan = HoppingPlan(**json.loads((OUT/'hopping_plan.json').read_text())['plan'])
    contig = OFDMPlan(**json.loads((OUT/'selection.json').read_text())['plan'])
    protocol = dict(seed=2026092901, draws=10000, family_alpha=.01, family_size=6,
        total_reference_and_sample_s=[20., 100.], differential_residual_std_db=[0., .001, .01],
        correlation_length_ghz=10., correction='Common unknown gain offset and slope plus background and interfering gases; independent hop offsets also tested.',
        primary='Fixed WR3.4 hopping architecture, nonzero 0.001 dB residual, 20 seconds total, standard atmosphere at 45 degrees.',
        inference='Joint VOC and PM; absolute abundance remains dependent on reference truth.',
        systematic_bias='Separate worst case epsilon times L1 operator norm. Robust threshold adds that bias to the null threshold and charges it twice in the 95% power limit.',
        scope='Conditional simulated performance, no measurement, compliance or hardware certification.')
    write('evaluation_protocol.json', protocol)
    rows, statuses, resources = [], [], []
    for profile in ['standard', 'igra_01', 'igra_04', 'igra_07', 'igra_09']:
        for elevation in [30, 45, 60, 90]:
            path = OUT/f'{profile}_{elevation}_physics.npz'
            data = sliced(path)
            for total in [20., 100.]:
                for sigma in [0., .001, .01]:
                    try:
                        r = fit(data, plan, elevation=elevation, total_s=total, residual_db=sigma)
                    except (ValueError, np.linalg.LinAlgError) as exc:
                        statuses.append(dict(profile=profile, elevation=elevation, total_s=total, residual_std_db=sigma, status=str(exc)))
                        continue
                    statuses.append(dict(profile=profile, elevation=elevation, total_s=total, residual_std_db=sigma, status='evaluated'))
                    sd, h = r['sd'], r['operator']
                    for j, target in enumerate(TARGETS):
                        bias = .0001*np.abs(h[j]).sum()
                        rows.append(dict(profile=profile, elevation_deg=elevation, total_s=total,
                            residual_std_db=sigma, target=target, sd_ug_m3=sd[j],
                            local_lod95_ug_m3=(Z+norm.ppf(.95))*sd[j],
                            local_recall_at_1ug_pct=100*norm.sf(Z-1/sd[j]) if j < 3 else np.nan,
                            worst_bias_at_0p0001db_ug_m3=bias,
                            local_robust_lod95_ug_m3=(Z+norm.ppf(.95))*sd[j]+2*bias,
                            sensing_tones=int(r['mask'].sum()), target_condition=r['condition']))
                    if sigma == .001:
                        c = r['count']
                        resources.append(dict(profile=profile, elevation_deg=elevation, **c,
                            peak_radiated_power_w=float(max(r['power'].reshape(-1, 16).sum(1))),
                            energy_j=float(sum(r['power'])*2*c['charged_duration_s']),
                            occupied_instantaneous_hz=16*plan.spacing_hz, tuning_span_ghz=88.,
                            gaussian_input_rate_bps=r['gaussian_input_rate_bps'],
                            scheduled_qpsk_coded_bits_per_wall_second=2*c['payload']*len(plan.frequency_ghz)*2/total))
    pd.DataFrame(rows).to_csv(OUT/'sensitivity.csv', index=False)
    pd.DataFrame(statuses).to_csv(OUT/'case_status.csv', index=False)
    pd.DataFrame(resources).to_csv(OUT/'resources.csv', index=False)
    data = sliced(OUT/'standard_45_physics.npz')
    engineering = []
    for label, p, a, power, nf, independent in [
        ('hopping_design_requirement', plan, data, 23., 6., False),
        ('hopping_independent_unknown_gains', plan, data, 23., 6., True),
        ('hopping_receiver_noise_stress', plan, data, 23., 17., False),
        ('unamplified_converter_before_backoff', plan, data, -23., 17., False),
        ('contiguous_exact_spectrum', contig, sliced(OUT/'standard_45_physics.npz', False), 23., 6., False)]:
        try:
            r = fit(a, p, power_dbm=power, noise_figure_db=nf, independent_hop_gains=independent)
            engineering.append(dict(case=label, status='evaluated', tx_power_dbm=power, noise_figure_db=nf,
                local_lod95_ug_m3=((Z+norm.ppf(.95))*r['sd']).tolist(),
                sensing_tones=int(r['mask'].sum()), target_condition=r['condition']))
        except (ValueError, np.linalg.LinAlgError) as exc:
            engineering.append(dict(case=label, status='rejected', reason=str(exc), tx_power_dbm=power, noise_figure_db=nf))
    write('engineering_controls.json', engineering)
    controls = validation(data, plan)
    # Freeze the standard operator and test actual seasonal background mismatch.
    nominal = fit(data, plan)
    h, mask = nominal['operator'], nominal['mask']
    mismatch = []
    for profile in ['igra_01', 'igra_04', 'igra_07', 'igra_09']:
        other = sliced(OUT/f'{profile}_45_physics.npz')
        error = other['background_db'][mask]-data['background_db'][mask]
        bias = h@error
        for j, target in enumerate(TARGETS[:3]):
            mismatch.append(dict(profile=profile, target=target, apparent_concentration_bias_ug_m3=bias[j],
                bias_over_nominal_sd=bias[j]/nominal['sd'][j],
                scope='Background-only mismatch control; changed thermal noise and gain would require a full unmatched receiver likelihood.'))
    pd.DataFrame(mismatch).to_csv(OUT/'unknown_weather_failure.csv', index=False)
    write('evaluation_summary.json', dict(status='passed' if all(r['passed'] for r in controls) else 'failed',
        sensitivity_rows=len(rows), physical_cases=20, nonzero_calibration_power_controls=controls,
        engineering_controls=engineering, measured_validation=False))
    print(json.dumps(engineering, indent=2), flush=True)
    print(pd.DataFrame(controls).to_string(index=False), flush=True)
    if not all(r['passed'] for r in controls):
        raise RuntimeError('Calibration Monte Carlo validation failed')


if __name__ == '__main__':
    main()
