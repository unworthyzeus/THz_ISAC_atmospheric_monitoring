"""Independently replay saved payload sensing results and source hashes."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"results/payload_recall"


def main():
    manifest = json.loads((OUT/"manifest.json").read_text())
    checks = []
    for group in ["inputs", "code", "outputs"]:
        for name, expected in manifest[group].items():
            path = (OUT if group == "outputs" else ROOT)/name
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            checks.append((f"hash {group} {name}", actual == expected))
    data = np.load(OUT/"replay.npz")
    metrics = pd.read_csv(OUT/"detection_metrics.csv")
    errors = pd.read_csv(OUT/"concentration_errors.csv")
    truth = np.array([1., 1., 1., 49., 41., 90.])
    threshold = norm.isf(.01/6)
    jacobian = np.vstack((np.eye(5), [0, 0, 0, 1, 1]))
    for case, rows in metrics.groupby("case", sort=True):
        positive, null = data[case+"_positive"], data[case+"_null"]
        h, covariance, sd = data[case+"_operator"], data[case+"_covariance"], data[case+"_sd"]
        checks.append((case+" target identities", bool(np.allclose(h@data["design"], jacobian, atol=1e-5))))
        n = data["nuisance"]
        scaled_leak = np.linalg.norm(h@n, axis=1)/(np.linalg.norm(h, axis=1)*np.linalg.norm(n))
        checks.append((case+" nuisance removal", bool(np.max(scaled_leak) < 1e-10)))
        checks.append((case+" covariance", bool(np.allclose(np.diag(h@covariance@h.T), sd**2, rtol=1e-8))))
        family = 100*np.mean(np.any(null/sd >= threshold, axis=1))
        checks.append((case+" family null rate", bool(family <= 1.1)))
        for j, (_, row) in enumerate(rows.iterrows()):
            tp = int(np.sum(positive[:, j] >= threshold*sd[j]))
            fp = int(np.sum(null[:, j] >= threshold*sd[j]))
            checks.append((case+" "+row.target+" confusion counts", tp == row.tp and fp == row.fp
                           and row.fn == len(positive)-tp and row.tn == len(null)-fp))
            checks.append((case+" "+row.target+" family replay", bool(np.isclose(family, row.family_false_alarm_pct))))
            predicted = norm.sf(threshold-truth[j]/sd[j])
            uncertainty = np.sqrt(predicted*(1-predicted)/len(positive))
            checks.append((case+" "+row.target+" analytic power", abs(tp/len(positive)-predicted) < 4*uncertainty+.001))
            old = errors[(errors.case == case) & (errors.target == row.target)].iloc[0]
            rmse = np.sqrt(np.mean((positive[:, j]-truth[j])**2))
            checks.append((case+" "+row.target+" RMSE replay", bool(np.isclose(rmse, old.rmse_ug_m3, rtol=1e-10))))
            checks.append((case+" "+row.target+" null variance", bool(.95 < null[:, j].var(ddof=1)/sd[j]**2 < 1.05)))
    resources = pd.read_csv(OUT/"resources.csv")
    for _, row in resources.iterrows():
        checks.append((f"resources {row.elapsed_s}", row.total == row.pilots+row.payload
                       and row.total == np.floor(row.elapsed_s/.01)*10000
                       and row.added_pilots == 0 and row.added_payload == 0
                       and np.isclose(row.total_radiated_energy_j, row.transmit_power_w*row.elapsed_s)))
    control = json.loads((OUT/"waveform_control.json").read_text())
    checks.append(("waveform untouched", control["identical_decisions"] and control["received_samples_unchanged"]
                   and control["additional_transmitted_symbols"] == 0))
    raw = pd.read_csv(OUT/"raw_symbol_validation.csv")
    checks.append(("raw moment variance validation", bool(raw.passed.all() and (raw.invalid == 0).all())))
    checks.append(("no omitted cases", len(json.loads((OUT/"failed_cases.json").read_text())) == 0 and len(metrics) == 72))
    # Historical baseline is independently reproduced analytically, not by
    # matching its random outcomes or reusing its test samples.
    previous = pd.read_csv(ROOT/"results/task_completion/detection_metrics.csv")
    prior = previous[(previous.band == "multiband_reference") & (previous.nuisance_policy == "reference_calibration")
                     & (previous.elapsed_s == 10) & (previous.residual_std_db == 0)]
    current = metrics[(metrics.method == "pilots") & (metrics.elapsed_s == 10) & (metrics.residual_std_db == 0)]
    checks.append(("unchanged pilot baseline", bool(np.allclose(prior.standard_error_ug_m3, current.standard_error_ug_m3, rtol=1e-8))))
    result = dict(status="passed" if all(ok for _, ok in checks) else "failed", checks=len(checks),
                  failures=[label for label, ok in checks if not ok],
                  detector_cases=int(metrics.case.nunique()), detection_rows=len(metrics),
                  limitation="Numerical and simulated-response verification, not field validation")
    (OUT/"verification.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
    if result["status"] != "passed":
        sys.exit(1)


if __name__ == "__main__":
    main()
