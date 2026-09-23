"""Replay closure evidence, preserve old scientific hashes and verify/seal a snapshot.

Run without --seal to check the saved snapshot. Sealing is an explicit action
after reviewing intentional numerical/source/document changes, not an auto-fix.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/five_task_closure"
OLD = ROOT / "results/task_completion"
sys.path.insert(0, str(ROOT / "src"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_text_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def snapshot_sha(path):
    if path.suffix in (".py", ".md", ".tex") or path.name.startswith("requirements") or path.name in (".gitattributes", ".gitignore"):
        return source_text_sha(path)
    return sha(path)


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def near(actual, expected, rtol=1e-8, atol=1e-10):
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol)


def check_sources():
    acquisition = read("public_acquisition.json")
    records = [acquisition["metadata"], *acquisition["records"], *read("additional_source_acquisition.json")]
    acquired = [r for r in records if r["status"] == "acquired"]
    for record in acquired:
        path = ROOT / record["file"]
        assert sha(path) == record["sha256"], str(path)
        if "source_checksum" in record:
            check = record["source_checksum"]
            assert hashlib.new(check["type"].lower(), path.read_bytes()).hexdigest() == check["value"]
    historical = json.loads((OLD / "completion_manifest.json").read_text())
    saved_text = read("closure_manifest.json").get("historical_source_text", {}) if (OUT / "closure_manifest.json").exists() else {}
    count = 0
    for section in ("outputs", "code", "inputs", "experiment_inputs"):
        base = OLD if section == "outputs" else ROOT
        for path, digest in historical[section].items():
            exact = sha(base / path) == digest
            normalized_match = section == "code" and saved_text.get(path) == source_text_sha(base / path)
            assert exact or normalized_match, f"Historical scientific content changed: {path}"
            count += 1
    changed_docs = []
    for path, digest in historical["documentation"].items():
        if sha(ROOT / path) != digest and saved_text.get(path) != source_text_sha(ROOT / path):
            changed_docs.append(path)
    assert changed_docs == ["README.md"], changed_docs
    return dict(acquired_source_hashes=len(acquired), dataset_repository_checksums=sum("source_checksum" in r for r in acquired),
                unavailable_downloads=sum(r["status"] != "acquired" for r in records),
                historical_scientific_hashes_preserved=count, historical_documentation_superseded=changed_docs)


def replay_aerosol():
    # Independent FFT implementation; do not call the production tds_transfer.
    records = [r for r in read("public_acquisition.json")["records"]
               if r.get("original_filename", "").startswith("corrected_mean_")]
    spectra, frequencies = {}, {}
    for r in records:
        time, signal = np.loadtxt(ROOT / r["file"]).T
        name = r["original_filename"]
        dt = (time[-1] - time[0]) / (len(time) - 1)
        frequencies[name] = np.fft.rfftfreq(len(time), dt * 1e-12) / 1e9
        spectra[name] = np.abs(np.fft.rfft(signal))
    before = sorted(n for n in spectra if "ref-avant" in n)
    after = sorted(n for n in spectra if "ref-apr" in n)
    f = frequencies[before[0]]
    f = f[(f >= 300) & (f <= 400)]
    assert len(f) == 4
    logamp = {n: np.interp(f, frequencies[n], np.log(spectra[n])) for n in spectra}
    blanks = {"before_geometric_mean": np.mean([logamp[n] for n in before], axis=0),
              "after_geometric_mean": np.mean([logamp[n] for n in after], axis=0)}
    frame = pd.read_csv(OUT / "calcite_measured_transmission.csv")
    for (sample, reference), rows in frame.groupby(["sample", "reference"]):
        near(rows.frequency_ghz, f)
        near(rows.attenuation_db, -20 / np.log(10) * (logamp[sample] - blanks[reference]))
    assert len(frame) == 64 and int((frame.attenuation_db < 0).sum()) == 42
    assert frame.mass_concentration_ug_m3.isna().all()
    drift = -20 / np.log(10) * (blanks["after_geometric_mean"] - blanks["before_geometric_mean"])
    near(pd.read_csv(OUT / "calcite_reference_drift.csv").after_vs_before_db, drift)
    near(read("calcite_validation.json")["before_after_max_abs_db"], np.max(np.abs(drift)))
    return dict(native_bins=len(f), measured_rows=len(frame), negative_values_retained=42)


def replay_pm():
    # Independent scaled least-squares projection; gas scaling leaves its span
    # unchanged, so the stored gas columns suffice for this nuisance check.
    physics = np.load(OLD / "physics_order4.npz")
    channel = np.load(OLD / "multiband_reference_channel.npz")
    mask = channel["sensing_mask"]
    std = np.sqrt(2 * (10 / np.log(10)) ** 2 / (30000 * channel["snr"][mask]))
    n = np.column_stack((np.ones(mask.sum()), physics["background_db"][:256][mask], physics["gas"][:256][mask])) / std[:, None]
    n /= np.linalg.norm(n, axis=0)
    a = physics["pm"][:256][mask] / std[:, None]
    projected = a - n @ np.linalg.lstsq(n, a, rcond=1e-12)[0]
    summary = read("pm_information_diagnosis.json")
    norms = np.linalg.norm(projected, axis=0)
    near(projected[:, 0] @ projected[:, 1] / np.prod(norms), summary["projected_fine_coarse_correlation"])
    near(1 / norms, summary["other_pm_known_std_ug_m3"])
    # Direct 2x2 inversion is only a cross-check; production uses stable SVD.
    cov = np.linalg.inv(projected.T @ projected)
    near(np.sqrt(np.diag(cov)), summary["fine_and_coarse_std_ug_m3"], rtol=1e-6)
    delta = np.array(summary["alternative_ug_m3"]) - summary["truth_ug_m3"]
    distance = np.linalg.norm(projected @ delta)
    near(distance, summary["optimized_nuisance_separation_in_noise_sd"], atol=1e-13)
    near(norm.cdf(-distance / 2), summary["gaussian_optimal_equal_prior_error"])
    frame = pd.read_csv(OUT / "pm_auxiliary_requirements.csv")
    for sigma in [1, 5, 10]:
        row = frame[(frame["case"] == "independent fine and total measurements") & (frame.auxiliary_sigma_ug_m3 == sigma)].iloc[0]
        near([row.fine_std_ug_m3, row.coarse_std_ug_m3, row.total_std_ug_m3], [sigma, np.sqrt(2) * sigma, sigma], rtol=1e-6)
    return dict(independent_pm_projection=True, auxiliary_information_cases=len(frame))


def replay_requirements_and_radio():
    limits = pd.read_csv(OLD / "detection_limits.csv")
    limits = limits[(limits.band == "multiband_reference") & (limits.nuisance_policy == "reference_calibration") &
                    (limits.elapsed_s == 10) & (limits.residual_std_db == 0) & (limits.bias_bound_db == 0)].set_index("target")
    radio = read("practical_radio_assessment.json")
    for row in read("environmental_requirement_assessment.json"):
        assert not row["evidence_complete"] and not row["compliance_demonstrated"]
        level = row["reference_ug_m3"]
        near(row["modeled_10s_lod_ug_m3"], limits.loc[row["target"], "detection_limit_ug_m3"])
        if level is not None:
            near(row["modeled_lod_to_reference_ratio"], row["modeled_10s_lod_ug_m3"] / level)
            near(row["single_pass_time_fraction"], radio["pass_duration_s"] / row["averaging_s"])
            near(row["conditional_detection_power_at_reference"], norm.sf(norm.isf(.01 / 6) - level / limits.loc[row["target"], "standard_error_ug_m3"]))
        else:
            assert row["averaging_s"] is None and row["conditional_detection_power_at_reference"] is None
    frame = pd.read_csv(OUT / "eband_moving_pass.csv")
    near(frame.modeled_rate_bps, frame.modeled_rate_bps.to_numpy()[::-1])
    near(frame.central_doppler_hz, -frame.central_doppler_hz.to_numpy()[::-1], atol=1e-7)
    near(frame.elevation_deg.iloc[[0, -1]], 45)
    near(np.trapezoid(frame.modeled_rate_bps, frame.time_from_zenith_s), radio["pass_information_bits"])
    near(radio["pass_information_bits"] / radio["pass_duration_s"], radio["pass_average_rate_bps"])
    snr = np.load(OLD / "eband_73p5GHz_channel.npz")["snr"]
    for coherent in [np.sinc(radio["one_percent_rate_loss_cfo_limit_hz"] / 1e6) ** 2,
                     np.exp(-radio["one_percent_rate_loss_phase_rms_rad"] ** 2)]:
        rate = np.log2(1 + coherent * snr / (1 + (1 - coherent) * snr)).sum()
        near(rate / np.log2(1 + snr).sum(), .99)
    from thz_isac.evidence_closure import ofdm_qpsk_control
    for saved in read("ofdm_waveform_controls.json"):
        replay = ofdm_qpsk_control(snr, seed=saved["seed"], normalized_cfo=saved["normalized_cfo"])
        for key in ("payload_bits", "bit_errors", "uncoded_ber", "identical_decisions"):
            assert replay[key] == saved[key], key
        assert saved["identical_decisions"]
        near(saved["uncoded_ber"], saved["bit_errors"] / saved["payload_bits"])
    water = pd.read_csv(OUT / "published_water_comparison.csv")
    summary = read("published_water_validation.json")
    for label in ("VNA", "TDS"):
        values = water.loc[water.instrument == label, "slope_db_per_m_per_g_m3"]
        near(values.mean(), summary[label.lower() + "_model_mean_slope"])
    assert summary["vna_within_reported_range"] and not summary["tds_within_reported_range"]
    return dict(requirement_cases=7, moving_pass_snapshots=len(frame), waveform_replays=3,
                published_water_states=len(water), tds_discrepancy_retained=True)


def check_paper_and_tests():
    build = read("paper_build.json")
    pdf = ROOT / build["output"]
    assert sha(pdf) == build["sha256"] == sha(ROOT / "paper/build/main.pdf")
    assert build["pages"] == 6 and not build["unresolved_references"] and not build["overfull_boxes"]
    text = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, encoding="utf-8", check=True).stdout
    assert "??" not in text
    compact = re.sub(r"\s+", "", text).upper()
    for token in ["56.21", "131.24", "12.94", "12,700", "0.2488", "0.090", "REFERENCES"]:
        assert token.upper() in compact, token
    assert pd.read_csv(OUT / "paired_measurement_schema.csv").empty
    testbytes = (OUT / "final_pytest.txt").read_bytes()
    testlog = testbytes.decode("utf-16" if testbytes.startswith(b"\xff\xfe") else "utf-8-sig")
    assert re.search(r"198 passed", testlog), testlog
    return dict(pdf_pages=build["pages"], test_count=198, empty_measurement_schema=True)


def snapshot():
    paths = set()
    for folder in ("src", "tests"):
        paths.update((ROOT / folder).rglob("*.py"))
    paths.update((ROOT / "src/thz_isac/data").glob("*"))
    paths.update((ROOT / "scripts").glob("*.py"))
    paths.update((ROOT / "paper").glob("*.tex"))
    paths.update((ROOT / "paper/history/2026-09-08").glob("*"))
    paths.update((ROOT / "docs").glob("*.md"))
    paths.update((ROOT / "results/task_completion").glob("*"))
    paths.update(p for p in OUT.glob("*") if p.name not in ("closure_manifest.json", "verification.json"))
    for name in (".gitattributes", ".gitignore", "README.md", "paper/README.md", "requirements-closure-lock.txt", "requirements-voc-pm.txt",
                 "requirements.txt", "output/pdf/thz_isac_pollutant_sensing_ieee.pdf", "paper/build/main.pdf"):
        paths.add(ROOT / name)
    return {p.relative_to(ROOT).as_posix(): snapshot_sha(p) for p in sorted(paths) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", action="store_true")
    args = parser.parse_args()
    evidence = {**check_sources(), **replay_aerosol(), **replay_pm(),
                **replay_requirements_and_radio(), **check_paper_and_tests()}
    hashes = snapshot()
    path = OUT / "closure_manifest.json"
    if args.seal:
        historical = json.loads((OLD / "completion_manifest.json").read_text())
        source_text = {p: source_text_sha(ROOT / p) for p in historical["code"]}
        source_text.update({p: source_text_sha(ROOT / p) for p in historical["documentation"] if p != "README.md"})
        path.write_text(json.dumps(dict(date="2026-09-23", scope="Public-data computational assessment; no atmospheric validation or compliance claim",
                                        hash_convention="SHA256; CRLF normalized to LF for Python/Markdown/TeX/requirements/Git configuration source; exact bytes for data/PDF",
                                        historical_source_text=source_text, files=hashes), indent=2) + "\n", encoding="utf-8")
    else:
        saved = read("closure_manifest.json")["files"]
        changes = sorted(p for p in set(saved) | set(hashes) if saved.get(p) != hashes.get(p))
        assert not changes, f"Snapshot differs; review before explicit --seal: {changes}"
    result = dict(status="passed", **evidence, snapshot_files=len(hashes),
                  seal_created=args.seal, scope="Numerical replay, provenance and artifact checks; no experimental-validation claim")
    (OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
