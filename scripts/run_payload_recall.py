"""Frozen comparison of pilot and passive payload absorption observables.

Uses the prior externally parameterized spectroscopy/channel arrays unchanged.
No target labels, thresholds, or frequencies are selected from test outcomes.
"""
from pathlib import Path
import hashlib
import json
import platform
import sys
import time
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from thz_isac.payload_sensing import (DB, resource_counts, attenuation_variance,
    draw_attenuation, attenuation_from_moments)
from thz_isac.attainable_estimation import efficient_linear_estimator
from thz_isac.concentration_units import natural_mass_design
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL
from thz_isac.retrieval_metrics import detection_metrics, concentration_errors

OUT = ROOT/"results/payload_recall"
PREVIOUS = ROOT/"results/task_completion"
TARGETS = ["H2CO", "CH3OH", "CH3CN", "PM2.5", "PMcoarse", "PM10"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def load_case(band):
    manifest = json.loads((PREVIOUS/"physics_manifest.json").read_text())
    source = PREVIOUS/"physics_order4.npz"
    if manifest["status"] != "passed" or sha(source) != manifest["outputs"][source.name]:
        raise ValueError("Prior physical input gate failed")
    data = np.load(source)
    names = manifest["gas_names"]
    gas = natural_mass_design(data["gas"], names, [MOLAR_MASS_G_MOL[n] for n in names])
    section = slice(0, 256) if band == "multiband_reference" else slice(256, 512)
    channel = dict(np.load(PREVIOUS/f"{band}_channel.npz"))
    mask = channel["sensing_mask"]
    d = np.column_stack((gas[section][mask, :3], data["pm"][section][mask]))
    n = np.column_stack((np.ones(mask.sum()), data["background_db"][section][mask], gas[section][mask, 3:]))
    return channel, d, n


def operator(design, nuisance, covariance):
    fit = efficient_linear_estimator(design, nuisance, covariance)
    h = np.vstack((fit.operator, fit.operator[-2]+fit.operator[-1]))
    return h, np.sqrt(np.diag(h@covariance@h.T))


def waveform_validation():
    """Independent raw symbols validate the moment approximation and failures."""
    rng = np.random.default_rng(2026092701)
    rows = []
    # Small blocks test the approximation more harshly than the main 9.97M.
    trials, symbols = 3000, 10000
    for snr in [10**.5, 5., 10., 30.]:
        for noise in [1., 1.1]:
            actual = .002
            estimates = []
            valid_count = 0
            for start in range(0, trials, 50):
                batch = min(50, trials-start)
                bits = rng.integers(0, 2, (batch, symbols, 2))*2-1
                x = (bits[..., 0]+1j*bits[..., 1])/np.sqrt(2)
                phase = np.exp(1j*np.linspace(-2, 2, symbols))
                y = np.sqrt(snr*10**(-actual/10))*x*phase
                y += np.sqrt(noise/2)*(rng.normal(size=y.shape)+1j*rng.normal(size=y.shape))
                q = np.abs(y)**2
                a, _, valid = attenuation_from_moments(q.mean(1), (q*q).mean(1), symbols, snr)
                valid_count += int(valid.sum())
                estimates.extend(a.tolist())
            est = np.array(estimates)
            expected = attenuation_variance(snr*10**(-actual/10)/noise, symbols, "m2m4")
            row = dict(snr=snr, noise_scale=noise, trials=trials, symbols=symbols,
                       true_attenuation_db=actual, invalid=trials-valid_count,
                       bias_db=float(np.mean(est-actual)), measured_variance_db2=float(est.var(ddof=1)),
                       predicted_variance_db2=float(expected), variance_ratio=float(est.var(ddof=1)/expected),
                       standardized_bias=float(np.mean(est-actual)/np.sqrt(expected/trials)))
            row["passed"] = bool(row["invalid"] == 0 and .9 < row["variance_ratio"] < 1.1 and abs(row["standardized_bias"]) < 4)
            rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/"raw_symbol_validation.csv", index=False)
    if not all(r["passed"] for r in rows):
        raise ValueError("Raw-symbol validation failed; retain outputs for diagnosis")

    # Actual FFT/CP modem replay: independent extension of the existing check.
    snr = np.load(PREVIOUS/"eband_73p5GHz_channel.npz")["snr"]
    rng = np.random.default_rng(2026092702)
    bits = rng.integers(0, 2, (10000, len(snr), 2))*2-1
    x = (bits[..., 0]+1j*bits[..., 1])/np.sqrt(2)
    h = np.sqrt(snr)*np.exp(1j*np.linspace(-.2, .2, len(snr)))
    wave = np.fft.ifft(x*h, axis=1, norm="ortho")
    cp = np.concatenate((wave[:, -16:], wave), axis=1)
    cp += (rng.normal(size=cp.shape)+1j*rng.normal(size=cp.shape))/np.sqrt(2)
    received = np.fft.fft(cp[:, 16:], axis=1, norm="ortho")
    hhat = (received[:30]/x[:30]).mean(0)
    eq = received[30:]/hhat
    before = np.stack((eq.real > 0, eq.imag > 0), axis=-1)
    saved_hash = hashlib.sha256(received.tobytes()).hexdigest()
    power = np.abs(received[30:])**2
    estimate, noise, valid = attenuation_from_moments(power.mean(0), (power*power).mean(0), 9970, snr)
    after = np.stack(((received[30:]/hhat).real > 0, (received[30:]/hhat).imag > 0), axis=-1)
    control = dict(payload_bits=before.size, bit_errors=int(np.count_nonzero(before != (bits[30:] > 0))),
        identical_decisions=bool(np.array_equal(before, after)),
        received_samples_unchanged=saved_hash == hashlib.sha256(received.tobytes()).hexdigest(),
        pilots=30, payload_symbols=9970, additional_transmitted_symbols=0,
        invalid_moment_tones=int((~valid).sum()), estimated_noise_median=float(np.median(noise)),
        attenuation_rmse_db=float(np.sqrt(np.mean(estimate**2))),
        scope="Uncoded QPSK, static per-tone magnitude, CP and FFT, ideal timing; no RF measurements or FEC")
    write("waveform_control.json", control)
    assert control["identical_decisions"] and control["received_samples_unchanged"]


def main():
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    protocol = dict(date="2026-09-27", seed=2026092703, draws_per_class=20000,
        family_alpha=.01, family_size=6, truth_ug_m3=[1., 1., 1., 49., 41., 90.],
        durations_s=[10., 100.], residual_std_db=[0., .001],
        methods=["pilots", "payload_energy_known_noise", "payload_m2m4"],
        threshold_selection="Fixed normal.isf(0.01/6), no test tuning",
        primary="1 ug/m3 VOC, 10 s, same broad reference, all three methods including failures",
        data="HITRAN/Mie/P.676-13 forward model from prior frozen arrays; observations simulated",
        signal_distribution="Exact complex mean and noncentral chi-square energy; M2M4 joint moment CLT, independently checked on raw complex symbols",
        stationary_assumption="Constant calibrated reference magnitude over the window; phase may vary for moment sensing",
        calibration="Same persistent correlated dB residual as prior study; separate bounded-bias stress",
        modulation="Constant modulus per active frequency, QPSK waveform control; no decoder oracle",
        resources="Original 1 us broad-reference symbols, 30/10000 pilots; only existing payload used",
        scope="Ideal multiband reference has no implementable RF band plan; E-band limitations retained",
        validation_selection="No parameters selected from waveform validation or detection outcomes",
        prior_local_manuscript="Preserved in Git stash: Preserve local September 8 manuscript before September 27 recall work")
    write("protocol.json", protocol)
    waveform_validation()
    print("Raw symbol and waveform validation passed", flush=True)
    channel, d, nuisance = load_case("multiband_reference")
    mask = channel["sensing_mask"]
    snr, f = channel["snr"][mask], channel["frequency_ghz"][mask]
    corr = np.exp(-np.abs(f[:, None]-f[None, :])/10.)
    chol_corr = np.linalg.cholesky(corr+np.eye(len(f))*1e-12)
    truth = np.array(protocol["truth_ug_m3"])
    signal = d@truth[:5]
    draws = protocol["draws_per_class"]
    zcrit = norm.isf(.01/6)
    metrics, errors, analytic, resources, stresses, information, failed = [], [], [], [], [], [], []
    arrays = dict(frequency_ghz=f, snr=snr, design=d, nuisance=nuisance)
    key_index = 0
    for elapsed in protocol["durations_s"]:
        counts = resource_counts(elapsed)
        resources.append(dict(elapsed_s=elapsed, **counts, transmit_power_w=float(channel["power_w"].sum()),
                              total_radiated_energy_j=float(channel["power_w"].sum()*elapsed),
                              added_pilots=0, added_payload=0, incremental_radio_rate_loss_pct=0.))
        for residual in protocol["residual_std_db"]:
            for method in protocol["methods"]:
                obs_method = dict(pilots="coherent", payload_energy_known_noise="energy_known_noise", payload_m2m4="m2m4")[method]
                n = counts["pilots"] if method == "pilots" else counts["payload"]
                variance = attenuation_variance(snr, n, obs_method)
                covariance = np.diag(variance)+residual**2*corr
                h, sd = operator(d, nuisance, covariance)
                key = f"case_{key_index:02d}"
                key_index += 1
                context = dict(case=key, method=method, elapsed_s=elapsed, residual_std_db=residual, symbols=n)
                # Identical seeds across methods for reproducibility; methods
                # consume different random variables, so this is NOT paired MC.
                rng = np.random.default_rng(protocol["seed"])
                anull, good_null = draw_attenuation(rng, np.zeros(len(f)), snr, n, draws, obs_method)
                apos, good_pos = draw_attenuation(rng, signal, snr, n, draws, obs_method)
                if not good_null.all() or not good_pos.all():
                    failed.append({**context, "invalid_null": int((~good_null).sum()), "invalid_positive": int((~good_pos).sum())})
                    raise ValueError("Moment inversion failed; no cases may be silently discarded")
                if residual:
                    anull += residual*rng.normal(size=anull.shape)@chol_corr.T
                    apos += residual*rng.normal(size=apos.shape)@chol_corr.T
                null, positive = anull@h.T, apos@h.T
                arrays[key+"_null"] = null
                arrays[key+"_positive"] = positive
                arrays[key+"_operator"] = h
                arrays[key+"_covariance"] = covariance
                arrays[key+"_sd"] = sd
                family_false = np.any(null/sd >= zcrit, axis=1)
                for j, target in enumerate(TARGETS):
                    row = detection_metrics(positive[:, j]/sd[j], null[:, j]/sd[j], zcrit)
                    for measure in ["precision", "recall", "false_positive"]:
                        lo, hi = row.pop(measure+"_ci95_pct")
                        row[measure+"_ci95_lower_pct"], row[measure+"_ci95_upper_pct"] = lo, hi
                    ap = average_precision_score(np.r_[np.zeros(draws), np.ones(draws)], np.r_[null[:, j], positive[:, j]])
                    metrics.append({**context, "target": target, "standard_error_ug_m3": sd[j],
                        "analytic_recall_pct": 100*norm.sf(zcrit-truth[j]/sd[j]),
                        "family_false_alarm_pct": 100*family_false.mean(), "average_precision_pct": 100*ap, **row})
                    errors.append({**context, "target": target, **concentration_errors(positive[:, j], truth[j])})
                    for concentration in ([1., 3., 10.] if j < 3 else [truth[j]]):
                        power = norm.sf(zcrit-concentration/sd[j])
                        for prevalence in [.01, .1, .5]:
                            analytic.append({**context, "target": target, "concentration_ug_m3": concentration,
                                "assumed_prevalence": prevalence, "conditional_recall_pct": 100*power,
                                "conditional_precision_pct": 100*prevalence*power/(prevalence*power+(1-prevalence)*.01/6),
                                "lod95_ug_m3": (zcrit+norm.ppf(.95))*sd[j]})
                    for epsilon in [0., 1e-5, 1e-4, 1e-3]:
                        bound = epsilon*np.abs(h[j]).sum()
                        stresses.append({**context, "target": target, "test": "bounded_bias",
                            "bias_bound_db": epsilon, "concentration_bias_bound_ug_m3": bound,
                            "robust_lod95_ug_m3": (zcrit+norm.ppf(.95))*sd[j]+2*bound,
                            "robust_recall_pct": 100*norm.sf(zcrit+(2*bound-truth[j])/sd[j])})
                if elapsed == 10 and residual == 0:
                    # Exact population noise mismatch plus actual response draws.
                    for scale in [.99, 1.01]:
                        changed, valid = draw_attenuation(rng, np.zeros(len(f)), snr, n, draws, obs_method, noise_scale=scale)
                        if not valid.all():
                            raise ValueError("Noise stress contains invalid estimates")
                        scores = changed@h.T/sd
                        for j, target in enumerate(TARGETS[:3]):
                            stresses.append({**context, "target": target, "test": "receiver_noise_scale",
                                "noise_scale": scale, "empirical_false_alarm_pct": 100*np.mean(scores[:, j] >= zcrit),
                                "mean_score": float(scores[:, j].mean())})
                    # Cross-target null: other VOCs and PM stay present.
                    for j, target in enumerate(TARGETS[:3]):
                        other = truth[:5].copy()
                        other[j] = 0.
                        mixed, valid = draw_attenuation(rng, d@other, snr, n, draws, obs_method)
                        if not valid.all():
                            raise ValueError("Mixed null contains invalid estimates")
                        scores = mixed@h[j]/sd[j]
                        stresses.append({**context, "target": target, "test": "other_targets_present_null",
                            "empirical_false_alarm_pct": 100*np.mean(scores >= zcrit), "mean_score": float(scores.mean())})
                print(context, "VOC recall", [round(r["recall_pct"], 3) for r in metrics[-6:-3]], flush=True)

    # First principles ceiling for the ORIGINAL pilot experiment: even an
    # oracle knowing every interferent cannot create information from ML.
    for band in ["multiband_reference", "eband_73p5GHz"]:
        ch, dd, nn = load_case(band)
        ss = ch["snr"][ch["sensing_mask"]]
        counts = resource_counts(10, symbol_duration_s=1e-6 if band == "multiband_reference" else 1.0625e-6)
        for method, n, tag in [("coherent", counts["pilots"], "pilots"), ("m2m4", counts["payload"], "payload_m2m4")]:
            vv = attenuation_variance(ss, n, method)
            oracle_sd = 1/np.sqrt(np.sum(dd[:, :3]**2/vv[:, None], axis=0))
            for j, target in enumerate(TARGETS[:3]):
                information.append(dict(band=band, method=tag, target=target,
                    all_other_parameters_known_sd_ug_m3=oracle_sd[j],
                    oracle_local_recall_pct=100*norm.sf(zcrit-1/oracle_sd[j]),
                    scope="Single target local Gaussian information ceiling; unachievable knowledge oracle"))
    # Leave each of the four public weather profiles out of its nuisance span.
    weather = pd.read_csv(PREVIOUS/"measured_weather_attenuation.csv")
    spectra = np.array([g.attenuation_db.to_numpy()[:256][mask] for _, g in weather.groupby("datetime")])
    dates = sorted(weather.datetime.unique())
    bg = np.load(PREVIOUS/"physics_order4.npz")["background_db"][:256][mask]
    variance = attenuation_variance(snr, resource_counts(10)["payload"], "m2m4")
    for heldout, date in enumerate(dates):
        training = spectra[np.arange(4) != heldout]-bg
        enhanced = np.column_stack((nuisance, training.T))
        hh, sd = operator(d, enhanced, np.diag(variance))
        bias = hh@(spectra[heldout]-bg)
        for j, target in enumerate(TARGETS[:3]):
            stresses.append(dict(method="payload_m2m4", elapsed_s=10., residual_std_db=0., target=target,
                test="heldout_weather_linear_diagnostic", heldout_date=date,
                standard_error_ug_m3=sd[j], background_bias_ug_m3=bias[j],
                scope="Unmodeled weather, fixed channel covariance; large bias invalidates local detection claims"))
    for name, table in dict(detection_metrics=metrics, concentration_errors=errors,
        conditional_curves=analytic, resources=resources, stress_tests=stresses,
        information_ceiling=information).items():
        pd.DataFrame(table).to_csv(OUT/(name+".csv"), index=False)
    np.savez_compressed(OUT/"replay.npz", **arrays)
    write("failed_cases.json", failed)
    frame = pd.DataFrame(metrics)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7), layout="constrained")
    colors = ["#798595", "#1691a2", "#e27d36"]
    for ax, target in zip(axes, TARGETS[:3]):
        selected = frame[(frame.elapsed_s == 10) & (frame.residual_std_db == 0) & (frame.target == target)]
        ax.bar(np.arange(3), selected.recall_pct, color=colors)
        ax.set(xticks=np.arange(3), xticklabels=["Pilots", "Energy\nknown noise", "Payload\nM2M4"],
               ylim=(0, 110), title=target, ylabel="Recall (%) at 1 µg/m³")
        for i, value in enumerate(selected.recall_pct):
            ax.text(i, value+2, f"{value:.3f}", ha="center", fontsize=9)
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("10 s, same transmitted symbols and power, 1% family false alarm budget\nConditional multiband simulation, calibrated stationary channel", fontsize=11)
    fig.savefig(OUT/"recall_comparison.png", dpi=180)
    fig.savefig(OUT/"recall_comparison.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
    curve = pd.DataFrame(analytic)
    for ax, target in zip(axes, TARGETS[:3]):
        for i, method in enumerate(protocol["methods"]):
            select = curve[(curve.elapsed_s == 10) & (curve.residual_std_db == 0) & (curve.target == target)
                           & (curve.method == method) & (curve.assumed_prevalence == .5)]
            ax.plot(select.concentration_ug_m3, select.conditional_recall_pct, "o-", color=colors[i], label=method)
        ax.set(xscale="log", xlabel="Concentration (µg/m³)", ylabel="Conditional recall (%)", title=target, ylim=(0, 105))
        ax.grid(alpha=.2)
    axes[0].legend(fontsize=7)
    fig.savefig(OUT/"concentration_curves.png", dpi=180)
    plt.close(fig)
    inputs = [PREVIOUS/"physics_order4.npz", PREVIOUS/"physics_manifest.json",
              PREVIOUS/"multiband_reference_channel.npz", PREVIOUS/"eband_73p5GHz_channel.npz",
              PREVIOUS/"measured_weather_attenuation.csv"]
    code = [Path(__file__), ROOT/"src/thz_isac/payload_sensing.py", ROOT/"src/thz_isac/attainable_estimation.py"]
    write("manifest.json", dict(status="completed", wall_seconds=time.perf_counter()-start,
        python=sys.version, platform=platform.platform(), numpy=np.__version__,
        inputs={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
        code={p.relative_to(ROOT).as_posix(): sha(p) for p in code},
        outputs={p.name: sha(p) for p in OUT.iterdir() if p.is_file()
                 and p.name not in {"manifest.json", "verification.json", "test_results.txt"}},
        limitations=["No measured atmospheric CSI", "M2M4 test responses use moment CLT", "No real multiband radio demonstrated",
                     "Persistent calibration and unknown weather are not cured by payload reuse", "QPSK resource comparison is not Gaussian-input capacity attainment"]))
    print("Payload recall experiment completed", flush=True)


if __name__ == "__main__":
    main()
