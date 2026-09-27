"""Charge an independent finite reference and test modulation model failure."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from thz_isac.payload_sensing import resource_counts, attenuation_variance, draw_attenuation, moment_power
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.retrieval_metrics import detection_metrics

OUT = ROOT/"results/payload_recall/finite_reference"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = dict(total_observation_s=20., reference_s=10., sensing_s=10., seed=2026092704,
        draws_per_class=20000, family_alpha=.01, family_size=6,
        target="Concentration enhancement over an independently measured baseline",
        absolute_concentration="Requires external knowledge of baseline concentration",
        reference="Independent noise; same background and stable calibration, no atmospheric evolution",
        comparisons="All methods charged identical reference plus sensing transmissions",
        purpose="Sensitivity to removing the exactly known reference assumption, secondary to primary protocol")
    (OUT/"protocol.json").write_text(json.dumps(protocol, indent=2)+"\n")
    base = np.load(ROOT/"results/payload_recall/replay.npz")
    d, n, snr = base["design"], base["nuisance"], base["snr"]
    counts = resource_counts(10)
    truth = np.array([1., 1., 1., 49., 41.])
    threshold = norm.isf(.01/6)
    rows, saved = [], {}
    for method in ["coherent", "energy_known_noise", "m2m4"]:
        symbols = counts["pilots"] if method == "coherent" else counts["payload"]
        c = 2*np.diag(attenuation_variance(snr, symbols, method))
        fit = efficient_linear_estimator(d, n, c)
        h = np.vstack((fit.operator, fit.operator[-2]+fit.operator[-1]))
        sd = np.sqrt(np.diag(h@c@h.T))
        rng = np.random.default_rng(protocol["seed"])
        null, v0 = draw_attenuation(rng, np.zeros(len(snr)), snr, symbols, 20000, method)
        ref0, v1 = draw_attenuation(rng, np.zeros(len(snr)), snr, symbols, 20000, method)
        pos, v2 = draw_attenuation(rng, d@truth, snr, symbols, 20000, method)
        ref1, v3 = draw_attenuation(rng, np.zeros(len(snr)), snr, symbols, 20000, method)
        assert all(v.all() for v in [v0, v1, v2, v3])
        null_est, pos_est = (null-ref0)@h.T, (pos-ref1)@h.T
        saved[method+"_null"], saved[method+"_positive"], saved[method+"_sd"] = null_est, pos_est, sd
        for j, name in enumerate(["H2CO", "CH3OH", "CH3CN", "PM2.5", "PMcoarse", "PM10"]):
            m = detection_metrics(pos_est[:, j]/sd[j], null_est[:, j]/sd[j], threshold)
            for label in ["precision", "recall", "false_positive"]:
                lower, upper = m.pop(label+"_ci95_pct")
                m[label+"_ci95_lower_pct"], m[label+"_ci95_upper_pct"] = lower, upper
            rows.append(dict(method=method, target=name, reference_s=10., sensing_s=10.,
                total_s=20., total_transmitted_symbols=2*counts["total"],
                total_energy_j=20*10**((23-30)/10), standard_error_ug_m3=sd[j], **m))
    pd.DataFrame(rows).to_csv(OUT/"detection_metrics.csv", index=False)
    np.savez_compressed(OUT/"replay.npz", **saved)

    # A misuse control: the PSK population formula is wrong for nonconstant
    # modulus QAM. No simulation is needed to demonstrate the systematic bias.
    constellation = (np.array([-3, -1, 1, 3])[:, None]+1j*np.array([-3, -1, 1, 3])[None, :]).ravel()/np.sqrt(10)
    kurtosis = float(np.mean(np.abs(constellation)**4))
    signal, noise = 5., 1.
    m2, m4 = signal+noise, kurtosis*signal**2+4*signal*noise+2*noise**2
    recovered, _, valid = moment_power(m2, m4, 10**12)
    wrong_db = float(-10*np.log10(recovered/signal))
    checks = dict(constellation="Normalized square 16-QAM", fourth_moment=kurtosis,
        true_attenuation_db=0., erroneous_psk_attenuation_db=wrong_db,
        implication="Use only with known constant modulus per-tone symbols; QAM requires its own moment/likelihood model",
        gaussian_noise="Impulsive distortion and nonlinear hardware also violate the model")
    (OUT/"modulation_mismatch.json").write_text(json.dumps(checks, indent=2)+"\n")
    failures = []
    for row in rows:
        method, j = row["method"], ["H2CO", "CH3OH", "CH3CN", "PM2.5", "PMcoarse", "PM10"].index(row["target"])
        pos, null, sd = saved[method+"_positive"], saved[method+"_null"], saved[method+"_sd"]
        if int(np.sum(pos[:, j] >= threshold*sd[j])) != row["tp"] or int(np.sum(null[:, j] >= threshold*sd[j])) != row["fp"]:
            failures.append(method+row["target"])
        expected = norm.sf(threshold-np.r_[truth, 90.][j]/sd[j])
        se = np.sqrt(expected*(1-expected)/20000)
        if abs(row["recall_pct"]/100-expected) > 4*se+.001:
            failures.append(method+row["target"]+" power")
    (OUT/"verification.json").write_text(json.dumps(dict(status="passed" if not failures else "failed", failures=failures), indent=2)+"\n")
    assert not failures
    manifest = dict(input_sha256=hashlib.sha256((ROOT/"results/payload_recall/replay.npz").read_bytes()).hexdigest(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json"})
    (OUT/"manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(pd.DataFrame(rows).query("target in ['H2CO','CH3OH','CH3CN']")[["method", "target", "recall_pct", "false_positive_rate_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
