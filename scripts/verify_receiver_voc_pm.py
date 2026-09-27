"""Replay expanded gas/PM controls and reject unstable size estimates."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from scipy.stats import binomtest, norm
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design/voc_pm_extension'


def main():
    checks = []
    def check(value, label):
        checks.append(label)
        if not value:
            raise AssertionError(label)
    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()
    acquisition = json.loads((OUT/'acquisition.json').read_text())
    check(sha(OUT/'lines.csv') == acquisition['processed_sha256'], 'acquired line bytes')
    for name, digest in json.loads((OUT/'physics_inputs.json').read_text()).items():
        check(sha(ROOT/name) == digest, 'physical input '+name)
    lines = pd.read_csv(OUT/'lines.csv')
    for row in acquisition['records']:
        if row['status'] == 'acquired':
            subset = lines[(lines.molecule == row['molecule']) & (lines.isotopologue_id == row['isotopologue_id'])]
            check(len(subset) == row['lines'], 'line count '+str(row['molecule'])+str(row['isotopologue_id']))
            check(subset.gamma_air.gt(0).all(), 'positive catalog widths')
    table = pd.read_csv(OUT/'response_controls.csv')
    for mode in ['original', 'expanded']:
        a = np.load(OUT/f'{mode}_20_0.0001.npz')
        h, d, n, c, sd = [a[k] for k in ['operator', 'design', 'nuisance', 'covariance', 'sd']]
        scale = np.linalg.norm(d, axis=0)
        check(np.max(abs(h[:len(scale)]@d*scale[:, None]/scale[None, :]-np.eye(len(scale)))) < 1e-5, 'scaled identity '+mode)
        check(np.linalg.norm(h@n)/(np.linalg.norm(h)*np.linalg.norm(n)) < 1e-12, 'nuisance rejection '+mode)
        check(np.allclose(sd**2, np.diag(h@c@h.T)), 'full covariance '+mode)
        check(np.allclose(h[-1], h[-2]+h[-3]), 'PM10 includes cross covariance '+mode)
        check(np.isclose(a['z'], norm.isf(.01/len(a['labels']))), 'family threshold '+mode)
        check(np.max(abs(a['null'].mean(axis=0)/sd))*100 < 5, 'null mean within five standard errors '+mode)
        check(np.max(abs(a['null'].var(axis=0)/sd**2-1)) < .07, 'null variance '+mode)
        truth = np.r_[a['truth'], a['truth'][-2:].sum()]
        check(np.max(abs((a['positive'].mean(axis=0)-truth)/sd))*100 < 5, 'mixture unbiased response '+mode)
        check(np.max(abs(a['positive'].var(axis=0)/sd**2-1)) < .07, 'mixture variance '+mode)
        false = int(np.any(a['null'] > a['z']*sd, axis=1).sum())
        check(binomtest(false, 10000, .01, alternative='greater').pvalue > .01/2, 'family false alarms '+mode)
        for row in table[table['mode'] == mode].itertuples():
            j = list(a['labels']).index(row.target)
            positive = a['positive'] if row.control == 'joint mixture' else a['limit_'+row.target]
            hits = int((positive[:, j] > a['z']*sd[j]).sum())
            ci = binomtest(hits, 10000).proportion_ci()
            check(hits == row.hits and row.family_false_count == false, 'count replay '+mode+row.target+row.control)
            check(np.isclose(ci.low*100, row.ci95_lower_pct) and np.isclose(ci.high*100, row.ci95_upper_pct), 'exact interval')
            if row.control == 'response limit':
                check(abs(hits/10000-.95) < 5*np.sqrt(.95*.05/10000)+.002, 'new gas power at limit')
                check(max(d[:, j]*row.concentration_ug_m3) < 1., 'weak absorption domain')
    diagnostics = json.loads((OUT/'diagnostics.json').read_text())
    for row in diagnostics:
        if row['mode'] == 'three_size_bins':
            check(row['status'].startswith('rejected'), 'unstable PM size split retained')
            a = np.load(OUT/f"three_size_bins_{int(row['total_s'])}_{row['residual_std_db']:g}.npz")
            d, h = a['design'], a['operator']
            scale = np.linalg.norm(d, axis=0)
            error = np.max(abs(h[:len(scale)]@d*scale[:, None]/scale[None, :]-np.eye(len(scale))))
            check(np.isclose(error, row['scaled_identity_error']) and error > 1e-5, 'size split numerical failure replay')
    sensitivity = pd.read_csv(OUT/'sensitivity.csv')
    check(not sensitivity['mode'].eq('three_size_bins').any(), 'no numerical failure presented as valid uncertainty')
    result = dict(status='passed', checks=len(checks), scope='Conditional arithmetic and retained failures; not measured gas/PM performance')
    (OUT/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
