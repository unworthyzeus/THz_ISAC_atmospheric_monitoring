"""Measured aerosol controls and a bounded published 380-GHz water comparison."""
from pathlib import Path
import hashlib
import json
import sys
import h5py
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann, Avogadro
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from thz_isac.evidence_closure import tds_transfer
from thz_isac.microwave_absorption import specific_attenuation
OUT = ROOT / "results/five_task_closure"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def aerosol():
    acquisition = json.loads((OUT / "public_acquisition.json").read_text())
    records = {r["original_filename"]: r for r in acquisition["records"] if "original_filename" in r}
    spectra, grids, resolutions, metadata = {}, {}, {}, []
    for name, record in records.items():
        path = ROOT / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        if name.startswith("corrected_mean_"):
            values = np.loadtxt(path)
            response = tds_transfer(values[:, 0], values[:, 1], values[:, 1])
            spectra[name] = response["sample_spectrum"]
            grids[name] = response["frequency_ghz"]
            resolutions[name] = response["resolution_ghz"]
        if path.suffix == ".h5":
            with h5py.File(path) as f:
                keys = sorted((key for key in f if key.isdigit()), key=int)
                attributes = sorted(set(k for key in keys for k in f[key].attrs))
                metadata.append(dict(file=name, traces=len(keys), samples_per_trace=len(f[keys[0]]),
                    start_timestamp=f[keys[0]].attrs["TIMESTAMP"], end_timestamp=f[keys[-1]].attrs["TIMESTAMP"],
                    trace_attributes=attributes, root_attributes=list(f.attrs),
                    nontrace_datasets=[key for key in f if not key.isdigit()]))
    before = sorted(name for name in spectra if "ref-avant" in name)
    after = sorted(name for name in spectra if "ref-apr" in name)
    sample_names = sorted(name for name in spectra if "mean_calcite" in name)
    frequency = grids[before[0]]
    mask = (frequency >= 300) & (frequency <= 400)
    frequency = frequency[mask]
    maximum_grid_shift = max(float(np.max(np.abs(grid[mask] - frequency))) for grid in grids.values())
    # Each acquisition has a slightly different native time step. Interpolate
    # log spectral amplitude onto the first blank's native (not padded) bins.
    amp = {name: np.exp(np.interp(frequency, grids[name], np.log(np.maximum(np.abs(spectrum), 1e-300))))
           for name, spectrum in spectra.items()}
    pre = np.exp(np.mean([np.log(amp[name]) for name in before], axis=0))
    post = np.exp(np.mean([np.log(amp[name]) for name in after], axis=0))
    rows = []
    for sample in sample_names:
        for baseline, ref in [("before_geometric_mean", pre), ("after_geometric_mean", post)]:
            for f, attenuation in zip(frequency, -20 * np.log10(amp[sample] / ref)):
                rows.append(dict(sample=sample, reference=baseline, frequency_ghz=f,
                    attenuation_db=attenuation, path_length_m=1., mass_concentration_ug_m3=None,
                    scope="Measured cell transmission; mass labels unavailable"))
    pd.DataFrame(rows).to_csv(OUT / "calcite_measured_transmission.csv", index=False)
    drift = -20 * np.log10(post / pre)
    pre_difference = -20 * np.log10(amp[before[1]] / amp[before[0]])
    post_difference = -20 * np.log10(amp[after[1]] / amp[after[0]])
    pd.DataFrame(dict(frequency_ghz=frequency, after_vs_before_db=drift,
        before_repeat_difference_db=pre_difference, after_repeat_difference_db=post_difference)).to_csv(OUT / "calcite_reference_drift.csv", index=False)
    means = pd.DataFrame(rows)
    negative = int((means.attenuation_db < 0).sum())
    summary = dict(dataset_doi="10.57745/DLJEFW", version="1.0", path_m=1,
        source_useful_lower_frequency_ghz=300, analysis_upper_frequency_ghz=400,
        selected_native_bins=frequency.tolist(), native_resolution_ghz=list(resolutions.values()),
        maximum_native_grid_shift_ghz=maximum_grid_shift,
        sample_recordings=len(sample_names), blank_recordings=len(before) + len(after),
        negative_attenuation_rows=negative, total_transmission_rows=len(rows),
        before_after_max_abs_db=float(np.max(np.abs(drift))),
        before_after_rms_db=float(np.sqrt(np.mean(drift ** 2))),
        within_before_max_abs_db=float(np.max(np.abs(pre_difference))),
        within_after_max_abs_db=float(np.max(np.abs(post_difference))),
        measured_attenuation_min_db=float(means.attenuation_db.min()),
        measured_attenuation_max_db=float(means.attenuation_db.max()),
        raw_metadata=metadata, concentration_labels_available=False, size_distribution_available=False,
        mass_extinction_calibration_possible=False,
        preprocessing="Native FFT without padding/window changes; log amplitudes interpolated between slightly different native grids; geometric mean of two blanks",
        uncertainty="Before/after and repeat-reference differences are diagnostics, not a universal covariance or confidence interval",
        conclusion="Measured aerosol-cell response is available, but concentration, size and background drift prevent PM mass-validation closure")
    write("calcite_validation.json", summary)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
    for i, name in enumerate(sample_names):
        sel = means[(means["sample"] == name) & (means.reference == "before_geometric_mean")]
        axes[0].plot(sel.frequency_ghz, sel.attenuation_db, marker="o", lw=1, label=f"Run {i+1}")
    axes[0].axhline(0, color="black", lw=.7)
    axes[0].set(xlabel="Frequency (GHz)", ylabel="Apparent attenuation over 1 m (dB)", title="Measured calcite runs vs. before blanks")
    axes[0].legend(ncol=2, fontsize=7)
    for vals, label in [(drift, "After / before"), (pre_difference, "Two before blanks"), (post_difference, "Two after blanks")]:
        axes[1].plot(frequency, vals, "o-", label=label)
    axes[1].axhline(0, color="black", lw=.7)
    axes[1].set(xlabel="Frequency (GHz)", ylabel="Reference difference (dB)", title="Measured reference sensitivity")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.savefig(OUT / "public_calcite_validation.png", dpi=180)
    fig.savefig(OUT / "public_calcite_validation.svg")
    plt.close(fig)
    return summary


def water():
    # Published Figure 8 slopes: VNA .033 +/- .009 and TDS .027 +/- .009,
    # units (dB/m)/(g/m3). Raw experimental rows are author-request only.
    # Our reproducible grid is a declared comparison envelope, not a recovery
    # of the authors' exact humidity/temperature sampling or regression.
    rows = []
    for pressure_pa, instrument in [(102700., "VNA"), (97400., "TDS")]:
        for temp_c in [20., 25., 30., 35., 40., 45.]:
            t = temp_c + 273.15
            saturation_pa = 610.78 * np.exp(17.27 * temp_c / (temp_c + 237.3))
            max_density = .95 * saturation_pa * .018015 / (8.314462618 * t) * 1000
            humidity = np.linspace(7.5, min(40.5, max_density), 20)
            e = humidity * 1e-3 / .018015 * 8.314462618 * t
            gamma = specific_attenuation(np.array([380.197353]), t, pressure_pa, e)["total"][:, 0] / 1000
            slope, intercept = np.polyfit(humidity, gamma, 1)
            rows.append(dict(instrument=instrument, temperature_c=temp_c, pressure_pa=pressure_pa,
                humidity_min_g_m3=humidity.min(), humidity_max_g_m3=humidity.max(),
                slope_db_per_m_per_g_m3=slope, intercept_db_per_m=intercept))
    pd.DataFrame(rows).to_csv(OUT / "published_water_comparison.csv", index=False)
    summary = dict(source="https://doi.org/10.1038/s41598-023-47586-8", source_locator="Figure 8 and experimental methods",
        frequency_ghz=380.197353, published_vna_slope=.033, published_vna_reported_plus_minus=.009,
        published_tds_slope=.027, published_tds_reported_plus_minus=.009,
        units="(dB/m)/(g/m3)", raw_measurements_available=False,
        observed_scope="Aggregate published water-vapour measurement, not VOC/PM or satellite validation",
        errorbar_interpretation="Reported plus/minus values; no confidence-level interpretation imposed",
        model_slope_min=min(r["slope_db_per_m_per_g_m3"] for r in rows),
        model_slope_max=max(r["slope_db_per_m_per_g_m3"] for r in rows),
        fitting="Separate linear slope per declared state over physically unsaturated humidity envelope")
    for instrument, observed in [("VNA", .033), ("TDS", .027)]:
        values = [r["slope_db_per_m_per_g_m3"] for r in rows if r["instrument"] == instrument]
        summary[instrument.lower() + "_model_mean_slope"] = float(np.mean(values))
        summary[instrument.lower() + "_within_reported_range"] = bool(all(abs(v - observed) <= .009 for v in values))
    write("published_water_validation.json", summary)
    fig, ax = plt.subplots(figsize=(6, 3.3), layout="constrained")
    frame = pd.DataFrame(rows)
    for i, (instrument, observed) in enumerate([("VNA", .033), ("TDS", .027)]):
        vals = frame.loc[frame.instrument == instrument, "slope_db_per_m_per_g_m3"]
        ax.errorbar(i - .08, observed, yerr=.009, fmt="o", capsize=5, color="C0", label="Published measurement ± reported range" if i == 0 else None)
        ax.plot(np.full(len(vals), i + .08), vals, "x", color="C1", label="Model across six temperature states" if i == 0 else None)
    ax.set(xticks=[0, 1], xticklabels=["VNA", "THz-TDS"], ylabel="Attenuation / water density\n[(dB/m)/(g/m³)]", title="Independent published 380 GHz comparison")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=.2)
    fig.savefig(OUT / "published_water_validation.png", dpi=180)
    fig.savefig(OUT / "published_water_validation.svg")
    plt.close(fig)
    return summary


if __name__ == "__main__":
    print(json.dumps(dict(calcite=aerosol(), water=water()), indent=2))
