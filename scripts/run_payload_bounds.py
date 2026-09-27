"""Fixed protocol: payload information, weather/elevation, and validated floors."""
from pathlib import Path
import hashlib
import json
import sys
import time
from dataclasses import replace
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm, binomtest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.payload_information import attenuation_crlb
from thz_isac.payload_sensing import attenuation_variance, resource_counts, draw_attenuation
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.robust_retrieval import ug_m3_to_ppm
from thz_isac.link_budget import LEOLinkBudgetConfig
from thz_isac.waveform_link import physical_channel_gain
from thz_isac.communication_capacity import waterfill_power

OUT = ROOT/'results/payload_bounds'
TARGETS = ['H2CO', 'CH3OH', 'CH3CN', 'PM2.5', 'PMcoarse', 'PM10']
Z = norm.isf(.01/6)
PROTOCOL = dict(seed=2026092801, draws_per_class=10000, family_alpha=.01, family_size=6,
    sensing_snr_min_db=5., minimum_sensing_tones=20,
    elevations_deg=[5, 15, 30, 45, 60, 90], profiles=['standard', 'igra_01', 'igra_04', 'igra_07', 'igra_09'],
    total_time_s=[2., 20., 100.], receiver_noise_multiplier=[1., 2.],
    noise_definition='Multiplier of total effective receiver input noise, including sky and electronics',
    differential_residual_std_db=[0., .0001, .001], correlation_length_ghz=10.,
    reference='Half of total transmission time is independent reference, half sample. Both are charged. Background and gain are matched and normalized.',
    sensitivity='Static elevation snapshots, matched known weather, recomputed ray, line shapes, atmospheric emission, link SNR and communication water filling',
    inference='Joint three VOCs and two PM modes; nuisance gain, background amplitude, CO/O3/SO2/NO2. Absolute concentration requires independently known reference abundance.',
    validation='All 30 physical cases, 20 seconds total, nominal receiver, zero residual. Untuned Bonferroni threshold. Separate null and per-VOC alternative samples.',
    limit='Local CRLB is an estimation variance bound, not a universal bound on classification or biased estimators. LOD uses Gaussian local response; validated with nonlinear moment inversion.',
    floor='Solve heteroscedastic positive-response variance before Monte Carlo. No fitting to test outcomes. Invalid inversion is a failure.',
    physics='Measured weather is public data; concentration profiles, PM composition and radio observations remain modeled.',
    waveform='Ideal simultaneous 256 separated 1 MHz tones over 60–400 GHz, QPSK, 30/10000 pilots, 1 us symbols; no implementable multiband modem claimed')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def fit_operator(d, nuisance, covariance):
    fit = efficient_linear_estimator(d, nuisance, covariance)
    h = np.vstack([fit.operator, fit.operator[-2]+fit.operator[-1]])
    sd = np.sqrt(np.diag(h@covariance@h.T))
    return h, sd


def positive_sd(h, d, j, concentration, snr, count, method, residual_cov):
    changed = snr*10**(-(d[:, j]*concentration)/10)
    v = attenuation_variance(changed, count, method)+attenuation_variance(snr, count, method)
    return np.sqrt((h[j]**2)@v+h[j]@residual_cov@h[j])


def corrected_floor(h, sd, d, j, snr, count, method, residual_cov):
    # The first crossing is the relevant limit; stay within a declared weak
    # absorption domain instead of extrapolating the trace model arbitrarily.
    local = (Z+norm.ppf(.95))*sd[j]
    upper = min(local*4, 1./max(d[:, j]))
    def equation(c):
        return c-Z*sd[j]-norm.ppf(.95)*positive_sd(h, d, j, c, snr, count, method, residual_cov)
    if equation(upper) < 0:
        return np.nan
    return brentq(equation, 0., upper)


def response_scores(rng, signal, snr, count, h, draws):
    result = []
    for start in range(0, draws, 1000):
        n = min(1000, draws-start)
        sample, valid = draw_attenuation(rng, signal, snr, count, n, 'm2m4')
        reference, valid_ref = draw_attenuation(rng, np.zeros_like(signal), snr, count, n, 'm2m4')
        if not valid.all() or not valid_ref.all():
            raise RuntimeError('Invalid moment estimate: no silent removal permitted')
        result.append((sample-reference)@h.T)
    return np.concatenate(result)


def validate_case(key, d, snr, h, sd, floors, case_index, count):
    rng = np.random.default_rng(PROTOCOL['seed']+case_index)
    draws = PROTOCOL['draws_per_class']
    null = response_scores(rng, np.zeros(len(snr)), snr, count, h, draws)
    saved = dict(null=null, design=d, snr=snr, operator=h, sd=sd, floors=floors)
    family = int(np.any(null > Z*sd, axis=1).sum())
    rows = []
    for j, target in enumerate(TARGETS[:3]):
        if not np.isfinite(floors[j]):
            raise RuntimeError(f'No in-domain detection limit for {key} {target}')
        positive = response_scores(rng, d[:, j]*floors[j], snr, count, h, draws)
        saved['positive_'+target] = positive
        hits = int((positive[:, j] > Z*sd[j]).sum())
        false = int((null[:, j] > Z*sd[j]).sum())
        ci = binomtest(hits, draws).proportion_ci(confidence_level=.95)
        # Fixed family of 90 power controls: 5 SE plus 0.2 pp approximation
        # allowance is specified before results; descriptive CIs retained.
        tolerance = 5*np.sqrt(.95*.05/draws)+.002
        passed = abs(hits/draws-.95) <= tolerance
        rows.append(dict(case=key, target=target, trials=draws, detection_limit_ug_m3=floors[j],
            recall_pct=100*hits/draws, recall_ci95_lower_pct=100*ci.low, recall_ci95_upper_pct=100*ci.high,
            false_positive_pct=100*false/draws, family_false_alarm_pct=100*family/draws,
            mean_null_ug_m3=float(null[:, j].mean()), variance_ratio=float(null[:, j].var(ddof=1)/sd[j]**2),
            mean_positive_ug_m3=float(positive[:, j].mean()), passed=passed))
    np.savez_compressed(OUT/(key+'_validation.npz'), **saved)
    return rows


def main():
    start = time.perf_counter()
    OUT.mkdir(exist_ok=True)
    write('protocol.json', PROTOCOL)
    if '--protocol-only' in sys.argv:
        return
    # Allows evaluation to overlap the expensive line integrations. The final
    # physics manifest and every consumed file hash are mandatory at closure.
    cases = pd.DataFrame([dict(case=f'{profile}_{el:02d}', profile=profile, elevation_deg=el)
        for profile in PROTOCOL['profiles'] for el in PROTOCOL['elevations_deg']])
    consumed = {}
    config = LEOLinkBudgetConfig(**json.loads((ROOT/'results/tables/physical_feasibility_config.json').read_text())['reference_link'])
    power_w = 10**((config.tx_power_dbm-30)/10)
    rows, validation, resources, information, statuses = [], [], [], [], []
    for index, case in cases.iterrows():
        path = OUT/(case['case']+'_physics.npz')
        while not path.exists() or time.time()-path.stat().st_mtime < 2:
            time.sleep(2)
        consumed[path.name] = sha(path)
        a = np.load(path)
        f = a['frequency_ghz']
        ground_km = float(a['ground_altitude_m'])/1000
        local_config = replace(config, earth_radius_km=config.earth_radius_km+ground_km,
                               satellite_altitude_km=config.satellite_altitude_km-ground_km)
        link = physical_channel_gain(f, a['background_db'], a['sky_temperature_k'], local_config, case.elevation_deg)
        for noise in PROTOCOL['receiver_noise_multiplier']:
            gain = link['gain_per_watt']/noise
            p = waterfill_power(gain, power_w)
            all_snr = gain*p
            mask = all_snr >= 10**.5
            snr = all_snr[mask]
            usable = mask.sum() >= PROTOCOL['minimum_sensing_tones']
            statuses.append(dict(case=case['case'], profile=case.profile, elevation_deg=case.elevation_deg,
                noise_multiplier=noise, sensing_tones=int(mask.sum()),
                status='eligible' if usable else 'insufficient_sensing_tones'))
            pd.DataFrame(statuses).to_csv(OUT/'case_status.csv', index=False)
            if not usable:
                print(case['case'], noise, 'rejected by fixed SNR/tone gate:', mask.sum(), flush=True)
                continue
            d = np.column_stack([a['gas'][mask, :3], a['pm'][mask]])
            nuisance = np.column_stack([np.ones(mask.sum()), a['background_db'][mask], a['gas'][mask, 3:]])
            corr = np.exp(-np.abs(f[mask, None]-f[None, mask])/10)
            one_q = attenuation_crlb(snr, 1, 'qpsk')
            one_r = attenuation_crlb(snr, 1, 'magnitude')
            for i, frequency in enumerate(f[mask]):
                m = 2*attenuation_variance(snr[i], 2, 'm2m4')
                information.append(dict(case=case['case'], noise_multiplier=noise, frequency_ghz=frequency,
                    snr_linear=snr[i], qpsk_bound_db2_per_sample=one_q[i], magnitude_bound_db2_per_sample=one_r[i],
                    m2m4_variance_db2_per_sample=m, magnitude_efficiency=one_r[i]/m, qpsk_efficiency=one_q[i]/m))
            for total in PROTOCOL['total_time_s']:
                count = resource_counts(total/2)
                resources.append(dict(case=case['case'], noise_multiplier=noise, total_s=total, reference_s=total/2,
                    sample_s=total/2, payload_per_window=count['payload'], pilots_per_window=count['pilots'],
                    radiated_energy_j=power_w*total, sensing_tones=int(mask.sum()), transmitted_tones=int((p>0).sum()),
                    transmit_power_w=float(p.sum()), extra_transmitted_symbols=0))
                for residual in PROTOCOL['differential_residual_std_db']:
                    rcov = residual**2*corr
                    methods = ['pilots', 'm2m4']+(['qpsk_crlb', 'magnitude_crlb'] if residual == 0 else [])
                    for method in methods:
                        n = count['pilots'] if method == 'pilots' else count['payload']
                        obs = 'coherent' if method == 'pilots' else 'm2m4'
                        v = 2*(one_q if method == 'qpsk_crlb' else one_r)/n if 'crlb' in method else 2*attenuation_variance(snr, n, obs)
                        covariance = np.diag(v)+rcov
                        h, sd = fit_operator(d, nuisance, covariance)
                        floors = np.full(3, np.nan)
                        for j, target in enumerate(TARGETS):
                            local = (Z+norm.ppf(.95))*sd[j]
                            if j < 3 and 'crlb' not in method:
                                floors[j] = corrected_floor(h, sd, d, j, snr, n, obs, rcov)
                            ppm = ug_m3_to_ppm(local, NATURAL_MOLAR_MASS_G_MOL[target], float(a['surface_temperature_k']), float(a['surface_pressure_pa'])) if j < 3 else np.nan
                            power = (100*norm.sf((Z*sd[j]-1)/positive_sd(h, d, j, 1., snr, n, obs, rcov))
                                     if j < 3 and 'crlb' not in method else np.nan)
                            rows.append(dict(case=case['case'], profile=case.profile, elevation_deg=case.elevation_deg,
                                noise_multiplier=noise, total_s=total, differential_residual_std_db=residual, method=method,
                                target=target, sd_ug_m3=sd[j], local_lod95_ug_m3=local, local_lod95_ppm=ppm,
                                response_lod95_ug_m3=floors[j] if j < 3 else np.nan,
                                response_lod95_ppm=ppm*floors[j]/local if j < 3 else np.nan,
                                recall_at_1ug_pct=power, sensing_tones=int(mask.sum())))
                        if noise == 1 and total == 20 and residual == 0 and method == 'm2m4':
                            validation.extend(validate_case(case['case'], d, snr, h, sd, floors, index, n))
        print(case['case'], 'screening complete; eligible configurations evaluated', flush=True)
        # Checkpoint complete rows; never mark a partial run passed.
        pd.DataFrame(rows).to_csv(OUT/'sensitivity.csv', index=False)
        pd.DataFrame(validation).to_csv(OUT/'detection_validation.csv', index=False)
    pd.DataFrame(resources).to_csv(OUT/'resources.csv', index=False)
    pd.DataFrame(information).to_csv(OUT/'information_efficiency.csv', index=False)
    while not (OUT/'physics_manifest.json').exists():
        time.sleep(2)
    physical = json.loads((OUT/'physics_manifest.json').read_text())
    if physical['status'] != 'passed' or any(physical['outputs'][name] != value for name, value in consumed.items()):
        raise RuntimeError('Physical reproduction/hash gate failed')
    passed = all(r['passed'] for r in validation)
    write('experiment_manifest.json', dict(status='passed' if passed else 'power_validation_failed',
        physical_cases=len(cases), validation_controls=len(validation), wall_seconds=time.perf_counter()-start,
        protocol_sha256=sha(OUT/'protocol.json'), physics_manifest_sha256=sha(OUT/'physics_manifest.json'),
        outputs={p.name: sha(p) for p in OUT.iterdir() if p.suffix in ['.csv', '.npz']},
        source_hashes={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), ROOT/'src/thz_isac/payload_information.py', ROOT/'src/thz_isac/payload_sensing.py']}))
    if not passed:
        raise RuntimeError('Power validation failed; inspect retained evidence')


if __name__ == '__main__':
    main()
