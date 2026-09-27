"""Exact additional gases and explicit PM size identifiability controls."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import norm, binomtest
from scipy.optimize import brentq
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL, DB_PER_NEPER, molecular_cross_section_cm2_per_molecule, concentration_ug_m3_to_number_density_cm3
from thz_isac.aerosol_mie import physical_diameter_from_aerodynamic, truncated_lognormal, mass_extinction
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.hopping_receiver import HoppingPlan
from thz_isac.payload_sensing import draw_attenuation, attenuation_variance
from design_payload_receiver import OUT as BASE, fit, sha
from evaluate_receiver_design import sliced
from receiver_design_physics import atmosphere, ray_for
OUT = BASE/'voc_pm_extension'
NAMES = ['CH3Cl', 'HCOOH']
# Natural molar masses from the same abridged standard atomic weights convention
# as the existing project. Isotope Doppler masses still come directly from HAPI.
MASSES = {'CH3Cl': 50.485, 'HCOOH': 46.025}


def initialize(lines, frequency):
    global LINES, FREQUENCY
    LINES = pd.read_csv(lines)
    FREQUENCY = frequency
    # Register only the adapter's supported gases in this process; do not rewrite
    # the historical source snapshot. Cross sections use HAPI isotope masses.
    MOLAR_MASS_G_MOL.update(MASSES)


def layer(task):
    name, t, p, density = task
    return DB_PER_NEPER*100*density*molecular_cross_section_cm2_per_molecule(
        LINES, FREQUENCY, name, temperature_k=t, pressure_pa=p)


def physics(plan):
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in
              [OUT/'lines.csv', OUT/'acquisition.json', BASE/'hopping_plan.json', BASE/'standard_45_physics.npz']}
    fingerprint = json.dumps(inputs, sort_keys=True)
    cache = OUT/'extra_physics.npz'
    if cache.exists():
        a = np.load(cache)
        if str(a['fingerprint']) != fingerprint:
            raise RuntimeError('Changed extension inputs: preserve the old cache before recomputing')
        return a['gas'], a['pm3']
    model, ground = atmosphere('standard')
    ray = ray_for(model, ground, 45., order=4)
    t, p, _, _ = model.state(ray.altitude_m)
    extra = []
    with ProcessPoolExecutor(max_workers=6, initializer=initialize, initargs=(str(OUT/'lines.csv'), plan.frequency_ghz)) as pool:
        for name in NAMES:
            density = concentration_ug_m3_to_number_density_cm3(1., MASSES[name])*np.exp(-ray.altitude_m/1500)
            layers = np.array(list(pool.map(layer, [(name, tt, pp, dd) for tt, pp, dd in zip(t, p, density)], chunksize=4)))
            extra.append(ray.path_weights_m@layers)
            print(name, 'integrated', flush=True)
    gas = np.column_stack(extra)
    # Same exploratory fine-particle composition as the prior model. Subdivide
    # its distribution at 1 micrometre aerodynamic diameter, with conditional
    # renormalization per unit mass; no new material identity is invented.
    pm = []
    for density, median, sd, lo, hi, index in [
        (1500., .5, 1.7, .03, 1., 1.5+.01j),
        (1500., .5, 1.7, 1., 2.5, 1.5+.01j),
        (1800., 4., 1.6, 2.5, 10., 1.53+.01j)]:
        bounds = physical_diameter_from_aerodynamic(np.array([lo, hi]), density)
        dist = truncated_lognormal(median, sd, *bounds, density, order=96)
        pm.append(mass_extinction(plan.frequency_ghz, dist, index)['extinction']*
                  DB_PER_NEPER*1e-9*(ray.path_weights_m@np.exp(-ray.altitude_m/1000)))
    pm3 = np.column_stack(pm)
    np.savez_compressed(cache, frequency_ghz=plan.frequency_ghz, gas=gas, pm3=pm3, fingerprint=fingerprint)
    (OUT/'physics_inputs.json').write_text(json.dumps(inputs, indent=2)+'\n')
    return gas, pm3


def scores(rng, signal, r, h, sigma):
    batches = []
    snr = r['snr'][r['mask']]
    factor = sigma*np.linalg.cholesky(r['correlation'])
    for _ in range(20):
        a, va = draw_attenuation(rng, signal, snr, r['count']['payload'], 500, 'm2m4')
        b, vb = draw_attenuation(rng, np.zeros(len(snr)), snr, r['count']['payload'], 500, 'm2m4')
        if not va.all() or not vb.all():
            raise RuntimeError('Invalid moment inversion')
        batches.append((a-b+rng.normal(size=a.shape)@factor.T)@h.T)
    return np.concatenate(batches)


def main():
    plan = HoppingPlan(**json.loads((BASE/'hopping_plan.json').read_text())['plan'])
    data = sliced(BASE/'standard_45_physics.npz')
    extra, pm3 = physics(plan)
    sensitivity, controls, diagnostics = [], [], []
    rng = np.random.default_rng(2026092904)
    gas_names = ['H2CO', 'CH3OH', 'CH3CN']+NAMES
    for duration, sigma in [(20., .0001), (20., .001), (100., .0001)]:
        r = fit(data, plan, total_s=duration, residual_db=sigma)
        for mode in ['original', 'expanded', 'three_size_bins']:
            gases = data['gas'][:, :3] if mode == 'original' else np.column_stack([data['gas'][:, :3], extra])
            names = gas_names[:3] if mode == 'original' else gas_names
            pm = pm3 if mode == 'three_size_bins' else data['pm']
            pm_names = ['PM1', 'PM1_to_2.5', 'PMcoarse'] if mode == 'three_size_bins' else ['PM2.5', 'PMcoarse']
            d = np.column_stack([gases, pm])[r['mask']]
            labels = names+pm_names+(['PM2.5', 'PM10'] if mode == 'three_size_bins' else ['PM10'])
            z = norm.isf(.01/len(labels))
            try:
                e = efficient_linear_estimator(d, r['nuisance'], r['covariance'])
                h = np.vstack([e.operator, e.operator[-3:-1].sum(axis=0), e.operator[-3:].sum(axis=0)]) if mode == 'three_size_bins' else np.vstack([e.operator, e.operator[-2:].sum(axis=0)])
                sd = np.sqrt(np.diag(h@r['covariance']@h.T))
                scales = np.linalg.norm(d, axis=0)
                identity_error = float(np.max(abs((e.operator@d)*scales[:, None]/scales[None, :]-np.eye(len(scales)))))
                status = 'rejected: unstable size separation' if identity_error > 1e-5 else 'local estimator computed'
                diagnostics.append(dict(mode=mode, total_s=duration, residual_std_db=sigma, status=status,
                    condition=e.target_condition, scaled_identity_error=identity_error))
                if identity_error > 1e-5:
                    np.savez_compressed(OUT/f'{mode}_{int(duration)}_{sigma:g}.npz', operator=h, design=d,
                        nuisance=r['nuisance'], covariance=r['covariance'], status=status, scaled_identity_error=identity_error)
                    continue
            except ValueError as exc:
                diagnostics.append(dict(mode=mode, total_s=duration, residual_std_db=sigma, status=str(exc)))
                continue
            key = f'{mode}_{int(duration)}_{sigma:g}'
            saved = dict(operator=h, design=d, sd=sd, nuisance=r['nuisance'], covariance=r['covariance'], z=z, labels=labels)
            for j, name in enumerate(labels):
                concentration = 1. if j < len(names) else (49. if name == 'PM2.5' else 90. if name == 'PM10' else 41. if name == 'PMcoarse' else np.nan)
                sensitivity.append(dict(mode=mode, total_s=duration, residual_std_db=sigma, target=name,
                    family_size=len(labels), sd_ug_m3=sd[j], local_lod95_ug_m3=(z+norm.ppf(.95))*sd[j],
                    comparison_concentration_ug_m3=concentration, predicted_recall_pct=100*norm.sf(z-concentration/sd[j]),
                    scope='Local modeled information only; large PM limits are not a valid concentration range'))
            if duration == 20 and sigma == .0001 and mode != 'three_size_bins':
                null = scores(rng, np.zeros(len(d)), r, h, sigma)
                saved['null'] = null
                false = int(np.any(null > z*sd, axis=1).sum())
                # One joint mixture: one unit of each VOC and the independently
                # retained public PM pair, fine 49 and coarse 41 ug/m3.
                truth = np.r_[np.ones(len(names)), 49., 41.]
                positive = scores(rng, d@truth, r, h, sigma)
                saved.update(positive=positive, truth=truth)
                for j, name in enumerate(labels):
                    hits = int((positive[:, j] > z*sd[j]).sum())
                    ci = binomtest(hits, 10000).proportion_ci()
                    controls.append(dict(mode=mode, target=name, control='joint mixture', concentration_ug_m3=np.r_[truth, 90.][j],
                        trials=10000, hits=hits, recall_pct=hits/100, ci95_lower_pct=ci.low*100, ci95_upper_pct=ci.high*100,
                        family_false_count=false, family_false_alarm_pct=false/100))
                # Validate new gas limits with positive-signal thermal variance.
                if mode == 'expanded':
                    snr = r['snr'][r['mask']]
                    count = r['count']['payload']
                    for j in [3, 4]:
                        def margin(c):
                            v = attenuation_variance(snr*10**(-d[:, j]*c/10), count, 'm2m4')+attenuation_variance(snr, count, 'm2m4')
                            psd = np.sqrt((h[j]**2)@v+sigma**2*h[j]@r['correlation']@h[j])
                            return c-z*sd[j]-norm.ppf(.95)*psd
                        upper = min((z+norm.ppf(.95))*sd[j]*4, 1/max(d[:, j]))
                        if margin(upper) < 0:
                            raise RuntimeError('New gas limit outside weak absorption domain')
                        limit = brentq(margin, 0, upper)
                        positive_limit = scores(rng, d[:, j]*limit, r, h, sigma)
                        saved['limit_'+names[j]] = positive_limit
                        saved['concentration_'+names[j]] = limit
                        hits = int((positive_limit[:, j] > z*sd[j]).sum())
                        ci = binomtest(hits, 10000).proportion_ci()
                        controls.append(dict(mode=mode, target=names[j], control='response limit', concentration_ug_m3=limit,
                            trials=10000, hits=hits, recall_pct=hits/100, ci95_lower_pct=ci.low*100, ci95_upper_pct=ci.high*100,
                            family_false_count=false, family_false_alarm_pct=false/100))
            np.savez_compressed(OUT/(key+'.npz'), **saved)
        # Oracle optimistic PM floor: all gas, other PM, and gain fixed.
        for j, name in enumerate(['PM2.5', 'PMcoarse']):
            column = data['pm'][r['mask'], j:j+1]
            for nuisance in [False, True]:
                n = r['nuisance'] if nuisance else np.empty((len(column), 0))
                e = efficient_linear_estimator(column, n, r['covariance'])
                sd = np.sqrt(e.covariance[0, 0])
                diagnostics.append(dict(mode='PM oracle with nuisance' if nuisance else 'PM oracle all other parameters known',
                    total_s=duration, residual_std_db=sigma, target=name, status='optimistic one parameter bound',
                    local_lod95_ug_m3=(norm.isf(.01/8)+norm.ppf(.95))*sd))
    pd.DataFrame(sensitivity).to_csv(OUT/'sensitivity.csv', index=False)
    pd.DataFrame(controls).to_csv(OUT/'response_controls.csv', index=False)
    (OUT/'diagnostics.json').write_text(json.dumps(diagnostics, indent=2)+'\n')
    print(pd.DataFrame(controls).to_string(index=False))
    print(pd.DataFrame(diagnostics).to_string(index=False))


if __name__ == '__main__':
    main()
