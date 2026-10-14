"""First principles CO channel example, with no receiver noise.

Run: python scripts/restart_co_observability.py
The first run fetches public HITRAN and JPL data. Subsequent runs use the saved
source files. This verifies algebra under stated assumptions, not detection
performance. Spectroscopic parameters are never fitted to an invented curve.
"""

from pathlib import Path
import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.constants import Boltzmann, atomic_mass, speed_of_light
from scipy.integrate import quad
from scipy.special import voigt_profile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/restart_2026_10_14"
SOURCE = OUT / "sources"
GHZ_PER_CM = 29.9792458
T = 296.0
P = 101325.0
WATER_P = 1000.0
CO_PPM = 1.0
CLOUD_START_M, CLOUD_END_M = 20.0, 40.0
MASS_KG = 27.994915 * atomic_mass


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire():
    SOURCE.mkdir(parents=True, exist_ok=True)
    raw = SOURCE / "CO_iso1_0_3000GHz.data"
    if not raw.exists():
        with contextlib.redirect_stdout(io.StringIO()):
            from hapi import db_begin, fetch
            db_begin(str(SOURCE))
            fetch("CO_iso1_0_3000GHz", 5, 1, 0, 3000 / GHZ_PER_CM)
        print("Downloaded CO line parameters from HITRAN.", flush=True)
    jpl = SOURCE / "jpl_c028001.cat"
    if not jpl.exists():
        with urllib.request.urlopen("https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat", timeout=30) as response:
            jpl.write_bytes(response.read())
    return raw, jpl


def read_lines(raw):
    rows = []
    for line in raw.read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        if len(line) < 160 or int(line[:2]) != 5 or int(line[2:3]) != 1:
            raise ValueError("Expected a complete HITRAN CO isotopologue 1 record.")
        rows.append({
            "nu_cm_1": float(line[3:15]), "S_296_cm_per_molecule": float(line[15:25]),
            "gamma_air_cm_1_atm": float(line[35:40]),
            "gamma_self_cm_1_atm": float(line[40:45]),
            "lower_energy_cm_1": float(line[45:55]), "n_air": float(line[55:59]),
            "delta_air_cm_1_atm": float(line[59:67]),
            "upper_v": line[67:82].strip(), "lower_v": line[82:97].strip(),
        })
    with (OUT / "co_line_parameters.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def cross_section(frequency_ghz, rows, pressure_atm=1.0):
    """At 296 K, use tabulated S directly and the trace gas air broadening limit.

    HITRAN intensities already include the reference isotopic abundance.
    Only isotopologue 1 is retained. Humid air perturber corrections, line
    mixing and non-Voigt corrections are outside this first example.
    """
    result = np.zeros_like(frequency_ghz)
    nu_grid = frequency_ghz / GHZ_PER_CM
    for row in rows:
        center = row["nu_cm_1"] + row["delta_air_cm_1_atm"] * pressure_atm
        doppler_std = row["nu_cm_1"] * np.sqrt(Boltzmann * T / MASS_KG) / speed_of_light
        gamma = row["gamma_air_cm_1_atm"] * pressure_atm
        result += row["S_296_cm_per_molecule"] * voigt_profile(nu_grid - center, doppler_std, gamma)
    return result


def main(check_hapi=False):
    raw, jpl_path = acquire()
    rows = read_lines(raw)
    jpl_centers = np.array([float(line[:13]) / 1000 for line in jpl_path.read_text().splitlines() if line.strip()])
    jpl_centers = jpl_centers[(jpl_centers >= 60) & (jpl_centers <= 1000)]
    ground = [r for r in rows if r["upper_v"] == "0" and r["lower_v"] == "0"
              and 60 <= r["nu_cm_1"] * GHZ_PER_CM <= 1000]
    centers = np.array([r["nu_cm_1"] * GHZ_PER_CM for r in ground])
    shifted = np.array([(r["nu_cm_1"] + r["delta_air_cm_1_atm"]) * GHZ_PER_CM for r in ground])
    assert len(ground) == len(jpl_centers) == 8
    center_error_mhz = np.max(np.abs(np.sort(centers) - np.sort(jpl_centers))) * 1000
    assert center_error_mhz < 0.2, center_error_mhz

    f = np.unique(np.r_[np.linspace(60, 1000, 4701), centers, shifted])
    lengths = np.arange(1.0, 201.0)
    cloud_length = np.clip(lengths - CLOUD_START_M, 0, CLOUD_END_M - CLOUD_START_M)
    sigma_cm2 = cross_section(f, rows)
    hapi_relative_error = None
    if check_hapi:
        check_f = np.array([110., centers[0], centers[1], centers[2], centers[-1]])
        with contextlib.redirect_stdout(io.StringIO()):
            import hapi
            hapi.db_begin(str(SOURCE))
            _, reference_sigma = hapi.absorptionCoefficient_Voigt(
                SourceTables="CO_iso1_0_3000GHz", Environment={"T": T, "p": 1.},
                WavenumberGrid=check_f / GHZ_PER_CM, WavenumberWing=200.,
                WavenumberWingHW=0., HITRAN_units=True, Diluent={"air": 1.})
        hapi_relative_error = float(np.max(abs(reference_sigma / cross_section(check_f, rows) - 1)))
        assert hapi_relative_error < 1e-7
    # cm2/molecule * molecules/m3 * 1e-4 m2/cm2 = 1/m.
    n_air_m3 = P / (Boltzmann * T)
    alpha_co = sigma_cm2 * 1e-4 * n_air_m3 * CO_PPM * 1e-6
    tau_co = alpha_co[:, None] * cloud_length[None, :]

    # Load only the independently sourced P.676 background module.
    module_path = ROOT / "src/thz_isac/microwave_absorption.py"
    spec = importlib.util.spec_from_file_location("restart_itu_background", module_path)
    itu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(itu)
    gamma_db_km = np.asarray(itu.specific_attenuation(f, T, P, WATER_P)["total"]).reshape(-1)
    tau_m = gamma_db_km[:, None] * (lengths[None, :] / 1000) * np.log(10) / 10
    h_fs = speed_of_light / (4 * np.pi * f[:, None] * 1e9 * lengths[None, :])
    h0_abs = h_fs * np.exp(-tau_m / 2)
    h_abs = h0_abs * np.exp(-tau_co / 2)
    recovered_tau = -2 * np.log(h_abs / h0_abs)
    extra_db = 10 / np.log(10) * recovered_tau
    tau_error = float(np.max(np.abs(recovered_tau - tau_co)))
    assert tau_error < 2e-15
    assert np.all(recovered_tau[:, lengths <= CLOUD_START_M] == 0)
    assert np.allclose(recovered_tau[:, lengths >= CLOUD_END_M], recovered_tau[:, -1, None], atol=2e-15)

    valid = cloud_length > 0
    # Invert a fixed known spectral template for column, then concentration.
    estimated_column_m2 = np.einsum("f,fl->l", sigma_cm2 * 1e-4, recovered_tau) / np.sum((sigma_cm2 * 1e-4)**2)
    estimated_ppm = estimated_column_m2[valid] / (n_air_m3 * cloud_length[valid]) * 1e6
    assert np.max(np.abs(estimated_ppm - CO_PPM)) < 1e-8

    first = min(ground, key=lambda row: row["nu_cm_1"])
    gamma = first["gamma_air_cm_1_atm"]
    doppler_std = first["nu_cm_1"] * np.sqrt(Boltzmann * T / MASS_KG) / speed_of_light
    area, _ = quad(lambda x: voigt_profile(x, doppler_std, gamma), -np.inf, np.inf)
    assert abs(area - 1) < 1e-8
    # The same channel has two factorizations if the background is unconstrained.
    alternative_h = h_fs * np.exp(-(tau_m + tau_co) / 2)
    ambiguity_error = float(np.max(abs(alternative_h / h_abs - 1)))
    exponent_roundoff = 4 * np.finfo(float).eps * (1 + np.max(tau_m + tau_co))
    assert ambiguity_error <= exponent_roundoff

    spectrum_rows = []
    for row, center in zip(ground, centers):
        k = int(np.argmin(abs(f - center)))
        spectrum_rows.append({"center_ghz": float(center),
            "air_hwhm_ghz_at_296K_1atm": row["gamma_air_cm_1_atm"] * GHZ_PER_CM,
            "background_db_at_200m": float(10 / np.log(10) * tau_m[k, -1]),
            "co_extra_db_for_1ppm_20m": float(extra_db[k, -1]),
            "co_amplitude_transmission": float(np.exp(-tau_co[k, -1] / 2))})
    with (OUT / "co_line_examples.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(spectrum_rows[0]))
        writer.writeheader()
        writer.writerows(spectrum_rows)
    np.savez_compressed(OUT / "channel_matrices.npz", frequency_ghz=f, length_m=lengths,
                        h_abs=h_abs, h0_abs=h0_abs, a_c_abs=np.exp(-tau_co / 2),
                        tau_co=tau_co, recovered_tau=recovered_tau)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), layout="constrained")
    fig.suptitle("CO in h(f, l): isolate the gas with a matched atmospheric reference", fontsize=16, weight="bold")
    ax = axes[0, 0]
    im = ax.pcolormesh(f, lengths, (20 * np.log10(h_abs)).T, shading="auto", cmap="viridis", rasterized=True)
    fig.colorbar(im, ax=ax, label="Channel magnitude (dB)")
    ax.set(title="1. Modeled channel magnitude", xlabel="Frequency (GHz)", ylabel="Path length l (m)")
    ax = axes[0, 1]
    im = ax.pcolormesh(f, lengths, extra_db.T, shading="auto", cmap="magma", rasterized=True)
    fig.colorbar(im, ax=ax, label="Extra CO loss (dB)")
    ax.axhline(CLOUD_START_M, color="white", lw=0.8, linestyle=":")
    ax.axhline(CLOUD_END_M, color="white", lw=0.8, linestyle=":")
    ax.set(title="2. Recover CO: -20 log10(|h| / |h0|)", xlabel="Frequency (GHz)", ylabel="Path length l (m)")
    ax = axes[1, 0]
    ax.plot(f, extra_db[:, -1], color="#117585", lw=1.6)
    for center in centers:
        ax.axvline(center, color="#a4b4bf", lw=0.6, linestyle=":")
    ax.set(title="3. Broadened rotational lines, 60 to 1000 GHz", xlabel="Frequency (GHz)", ylabel="Extra CO loss after the cloud (dB)")
    ax.grid(alpha=0.15)
    ax = axes[1, 1]
    f_local = np.linspace(100, 130, 3001)
    for pressure, color in [(1.0, "#117585"), (0.1, "#c26b32")]:
        shape = cross_section(f_local, [first], pressure) / (first["S_296_cm_per_molecule"] * GHZ_PER_CM)
        ax.plot(f_local, shape, color=color, label=f"{pressure:g} atm")
    ax.axvline(first["nu_cm_1"] * GHZ_PER_CM, color="black", lw=0.7, linestyle=":", label="Unshifted line center")
    ax.set(title="4. One transition has a continuous profile", xlabel="Frequency (GHz)", ylabel="Area normalized profile (1/GHz)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.15)
    fig.supxlabel("Assumed case: 296 K, 1 atm, water partial pressure 1000 Pa; 1 ppm excess CO between 20 and 40 m.\nHITRAN main isotopologue + ITU P.676; exact background and calibration; no receiver noise. Simulation, not a detection limit.", fontsize=9)
    fig.savefig(OUT / "co_observability.png", dpi=180)
    fig.savefig(OUT / "co_observability.pdf")
    plt.close(fig)

    # A separate path plot exposes what l contributes and where it contributes nothing new.
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for center in centers[:3]:
        k = int(np.argmin(abs(f - center)))
        ax.plot(lengths, extra_db[k], label=f"{center:.3f} GHz")
    ax.axvspan(CLOUD_START_M, CLOUD_END_M, color="#a9cfd2", alpha=0.3, label="CO cloud")
    ax.set(xlabel="Path length l (m)", ylabel="Recovered extra loss (dB)", title="Extra loss stops growing once the ray has crossed the whole cloud")
    ax.legend(frameon=False)
    ax.grid(alpha=0.15)
    fig.savefig(OUT / "co_path_length.png", dpi=180)
    plt.close(fig)

    manifest = {
        "study_date": "2026-10-14", "purpose": "Noiseless observability and line broadening demonstration",
        "assumptions": {"temperature_k": T, "pressure_pa": P, "water_pressure_pa": WATER_P,
            "co_enhancement_ppm": CO_PPM, "cloud_interval_m": [CLOUD_START_M, CLOUD_END_M],
            "distance_equals_atmospheric_length": True, "exact_background_and_calibration": True,
            "phase": "Only magnitudes modeled; molecular dispersion not computed",
            "spectroscopy": "HITRAN isotopologue 1, 296 K, trace limit air broadened Voigt, no wing cutoff within 0 to 3000 GHz catalog",
            "scenario_values": "Chosen inputs, not measured environmental conditions"},
        "sources": {"hitran": "https://hitran.org/hapi/", "hitran_request": "molecule 5, isotopologue 1, 0 to 3000/29.9792458 cm^-1",
            "jpl": "https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat",
            "itu": "https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf"},
        "checks": {"all_passed": True, "line_records": len(rows), "in_band_ground_state_lines": len(ground),
            "hapi_max_relative_cross_section_difference": hapi_relative_error,
            "max_hitran_jpl_center_difference_mhz": float(center_error_mhz),
            "matrix_shape_frequency_length": list(h_abs.shape), "max_optical_depth_recovery_error": tau_error,
            "max_recovered_ppm_error": float(np.max(abs(estimated_ppm - CO_PPM))),
            "single_line_integral": float(area), "zero_loss_before_cloud": True,
            "constant_loss_after_cloud": True, "unconstrained_background_ambiguity_verified": True,
            "ambiguity_max_relative_roundoff": ambiguity_error,
            "ambiguity_roundoff_tolerance": float(exponent_roundoff)},
        "limitations": ["No measured channel or demonstrated sensitivity", "No atmospheric or calibration uncertainty",
            "Minor isotopologues and non-Voigt effects omitted", "Far wing accuracy is not validated by this example",
            "The same forward model is used in recovery; this verifies inversion algebra only"],
        "sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in [raw, jpl_path, module_path,
            ROOT / "src/thz_isac/data/itu676_13_oxygen.csv", ROOT / "src/thz_isac/data/itu676_13_water.csv", Path(__file__)]},
    }
    save_json(OUT / "manifest.json", manifest)
    print(json.dumps({"checks": manifest["checks"], "line_examples": spectrum_rows[:3]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-hapi", action="store_true", help="Compare five cross sections with the HAPI implementation.")
    main(check_hapi=parser.parse_args().check_hapi)
