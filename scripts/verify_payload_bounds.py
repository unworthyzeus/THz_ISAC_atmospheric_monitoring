"""Independent replay of saved response counts, resources and inference identities."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm, binomtest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from thz_isac.concentration_units import NATURAL_MOLAR_MASS_G_MOL
from thz_isac.payload_sensing import attenuation_variance
OUT = ROOT/'results/payload_bounds'


def main():
    count = 0
    def check(condition, label):
        nonlocal count
        count += 1
        if not condition:
            raise AssertionError(label)
    manifest = json.loads((OUT/'experiment_manifest.json').read_text())
    check(manifest['status'] == 'passed', 'experiment gate')
    for name, key in [('protocol.json', 'protocol_sha256'), ('physics_manifest.json', 'physics_manifest_sha256')]:
        check(hashlib.sha256((OUT/name).read_bytes()).hexdigest() == manifest[key], 'protocol/physics snapshot '+name)
    physical_manifest = json.loads((OUT/'physics_manifest.json').read_text())
    check(hashlib.sha256((ROOT/'scripts/run_payload_physics.py').read_bytes()).hexdigest() == physical_manifest['inputs']['script'], 'physical driver provenance')
    check(hashlib.sha256((ROOT/'scripts/payload_physics_workers.py').read_bytes()).hexdigest() == physical_manifest['worker_sha256'], 'physical worker provenance')
    for name, digest in manifest['outputs'].items():
        check(hashlib.sha256((OUT/name).read_bytes()).hexdigest() == digest, 'output hash '+name)
    for name, digest in manifest['source_hashes'].items():
        check(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, 'source hash '+name)
    protocol = json.loads((OUT/'protocol.json').read_text())
    resources = pd.read_csv(OUT/'resources.csv')
    for r in resources.itertuples(index=False):
        check(r.reference_s+r.sample_s == r.total_s, 'charged reference time')
        frames = int(round(r.sample_s/.01))
        check(r.payload_per_window == frames*9970 and r.pilots_per_window == frames*30, 'frame resource counts')
        check(np.isclose(r.radiated_energy_j, 10**((23-30)/10)*r.total_s), 'energy budget')
        check(r.extra_transmitted_symbols == 0 and np.isclose(r.transmit_power_w, 10**(-.7)), 'unchanged transmissions')
    validation = pd.read_csv(OUT/'detection_validation.csv')
    data = pd.read_csv(OUT/'sensitivity.csv')
    z = norm.isf(.01/6)
    targets = ['H2CO', 'CH3OH', 'CH3CN', 'PM2.5', 'PMcoarse', 'PM10']
    for case, rows in validation.groupby('case'):
        a = np.load(OUT/(case+'_validation.npz'))
        null, h, sd, d, snr = [a[k] for k in ['null', 'operator', 'sd', 'design', 'snr']]
        eye = np.vstack([np.eye(5), [0, 0, 0, 1, 1]])
        check(np.allclose(h@d, eye, rtol=0, atol=1e-5), 'target identity '+case)
        check(np.allclose(h[-1], h[-2]+h[-3]), 'PM10 covariance contrast')
        physical = np.load(OUT/(case+'_physics.npz'))
        # Match retained frequencies using their deterministic SNR mask via D:
        # each retained row is a unique physical gas/PM response vector.
        all_d = np.column_stack([physical['gas'][:, :3], physical['pm']])
        indices = [int(np.argmin(np.linalg.norm(all_d-row, axis=1))) for row in d]
        n = np.column_stack([np.ones(len(indices)), physical['background_db'][indices], physical['gas'][indices, 3:]])
        nuisance_leak = np.max(abs(h@n)/(sd[:, None]*np.maximum(np.linalg.norm(n, axis=0), 1e-30)))
        check(nuisance_leak < 1e-6, 'scaled nuisance annihilation '+case)
        variance = 2*attenuation_variance(snr, 9970000, 'm2m4')
        expected = np.sqrt(np.sum(h*h*variance, axis=1))
        check(np.allclose(sd, expected, rtol=1e-8), 'variance replay '+case)
        family = int(np.any(null > z*sd, axis=1).sum())
        check(binomtest(family, len(null), .01, alternative='greater').pvalue >= .01/30, 'family false alarm '+case)
        for row in rows.itertuples(index=False):
            j = targets.index(row.target)
            positive = a['positive_'+row.target]
            hits = int((positive[:, j] > z*sd[j]).sum())
            false = int((null[:, j] > z*sd[j]).sum())
            check(np.isclose(hits/len(positive)*100, row.recall_pct), 'power count '+case+row.target)
            check(np.isclose(false/len(null)*100, row.false_positive_pct), 'null count '+case+row.target)
            check(np.isclose(family/len(null)*100, row.family_false_alarm_pct), 'family replay')
            check(binomtest(false, len(null), .01/6, alternative='greater').pvalue >= .01/90, 'per target false alarm')
            check(abs(null[:, j].mean())/(sd[j]/np.sqrt(len(null))) < 5, 'null bias')
            ratio = null[:, j].var(ddof=1)/sd[j]**2
            check(abs(ratio-1) < .07, 'variance control')
            local = data[(data['case'] == case)&(data.target == row.target)&(data.method == 'm2m4')&
                         (data.total_s == 20)&(data.noise_multiplier == 1)&(data.differential_residual_std_db == 0)].iloc[0]
            check(np.isclose(local.response_lod95_ug_m3, row.detection_limit_ug_m3), 'floor data consistency')
            ppm = row.detection_limit_ug_m3*8.314462618*float(physical['surface_temperature_k'])/(NATURAL_MOLAR_MASS_G_MOL[row.target]*float(physical['surface_pressure_pa']))
            check(np.isclose(ppm, local.response_lod95_ppm, rtol=1e-10), 'ppm conversion')
            ci = binomtest(hits, len(positive)).proportion_ci()
            check(np.isclose(100*ci.low, row.recall_ci95_lower_pct) and np.isclose(100*ci.high, row.recall_ci95_upper_pct), 'exact power interval')
    info = pd.read_csv(OUT/'information_efficiency.csv')
    oracle = 2*(10/np.log(10))**2/info.snr_linear
    check(np.all(oracle <= info.qpsk_bound_db2_per_sample*(1+1e-8)), 'known symbol oracle ordering')
    check(np.all(info.qpsk_bound_db2_per_sample <= info.magnitude_bound_db2_per_sample*(1+1e-8)), 'data processing ordering')
    check(np.all(info.magnitude_bound_db2_per_sample <= info.m2m4_variance_db2_per_sample*(1+1e-8)), 'moment efficiency ordering')
    status = pd.read_csv(OUT/'case_status.csv')
    check(len(status) == 60, 'all physical/noise combinations accounted for')
    check(set(validation['case']) == set(status[(status.noise_multiplier == 1)&(status.status == 'eligible')]['case']), 'no eligible validation case dropped')
    check(np.all((status.status == 'eligible') == (status.sensing_tones >= protocol['minimum_sensing_tones'])), 'fixed usable tone gate')
    moving = json.loads((OUT/'moving_geometry_manifest.json').read_text())
    check(moving['status'] == 'passed', 'moving geometry convergence')
    thermal = json.loads((OUT/'thermal_convergence.json').read_text())
    check(thermal['status'] == 'passed', 'thermal quadrature across all states')
    reproduction = pd.read_csv(OUT/'physics_reproduction.csv')
    check(reproduction.passed.all(), 'historical spectra reproduction')
    result = dict(status='passed', checks=count, physical_cases=30, eligible_nominal_cases=validation['case'].nunique(),
        power_controls=len(validation), maximum_family_false_alarm_pct=float(validation.family_false_alarm_pct.max()),
        family_test='Exact binomial upper test against 1% with Bonferroni over 30 physical cases',
        interpretation='Conditional numerical verification, not atmospheric field validation')
    (OUT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
