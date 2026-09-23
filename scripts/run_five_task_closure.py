"""Requirement assessment, practical link control and PM information diagnosis."""
from pathlib import Path
from dataclasses import asdict
import json
import sys
import numpy as np
import pandas as pd
from scipy.constants import Boltzmann, speed_of_light
from scipy.optimize import brentq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from thz_isac.evidence_closure import (requirement_assessment, projected_design,
    covariance_from_information_rows, conditional_power, ofdm_qpsk_control)
from thz_isac.waveform_link import (OFDMPlan, maximum_zenith_pass_s, physical_channel_gain,
    ofdm_coherent_fraction, impaired_spectral_efficiency)
from thz_isac.communication_capacity import waterfill_power
from thz_isac.atmospheric_profiles import StandardAtmosphere
from thz_isac.slant_path import satellite_slant_quadrature
from thz_isac.microwave_absorption import specific_attenuation, downwelling_brightness_k
from thz_isac.link_budget import LEOLinkBudgetConfig
from thz_isac.concentration_units import natural_mass_design
from thz_isac.physical_spectroscopy import MOLAR_MASS_G_MOL
OUT = ROOT / "results/five_task_closure"
PREVIOUS = ROOT / "results/task_completion"


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def standards():
    limits = pd.read_csv(PREVIOUS / "detection_limits.csv")
    ref = limits[(limits.band == "multiband_reference") & (limits.nuisance_policy == "reference_calibration")
                 & (limits.elapsed_s == 10) & (limits.residual_std_db == 0) & (limits.bias_bound_db == 0)].set_index("target")
    pass_s = maximum_zenith_pass_s(45)
    sources = {
        "WHO2021": "https://www.who.int/publications/i/item/9789240034228",
        "WHO2010": "https://www.ncbi.nlm.nih.gov/books/NBK138711/",
    }
    specs = [("PM2.5", 15., 86400., "ambient surface air", "WHO2021", "24-hour; 99th percentile across a year"),
             ("PM10", 45., 86400., "ambient surface air", "WHO2021", "24-hour; 99th percentile across a year"),
             ("PM2.5", 5., 365 * 86400., "ambient surface air", "WHO2021", "annual mean"),
             ("PM10", 15., 365 * 86400., "ambient surface air", "WHO2021", "annual mean"),
             ("H2CO", 100., 1800., "indoor air", "WHO2010", "30-minute indoor guideline"),
             ("CH3OH", None, 1., "no applicable guideline selected", "WHO2021", "absent from these guideline sets"),
             ("CH3CN", None, 1., "no applicable guideline selected", "WHO2021", "absent from these guideline sets")]
    rows = []
    for name, level, period, domain, source, averaging in specs:
        row = ref.loc[name]
        assessment = requirement_assessment(reference_domain=domain, measured_domain="modeled slant path with assumed profile",
            averaging_s=period, covered_s=pass_s, paired_reference=False, calibrated=False,
            limit_ug_m3=level, modeled_lod_ug_m3=float(row.detection_limit_ug_m3))
        rows.append(dict(target=name, reference_ug_m3=level, averaging_s=period if level is not None else None,
            averaging_definition=averaging, reference_domain=domain, source=sources[source],
            source_kind="Health guideline; not a legal certification or instrument accuracy specification",
            modeled_10s_lod_ug_m3=float(row.detection_limit_ug_m3),
            conditional_detection_power_at_reference=None if level is None else conditional_power(level, row.standard_error_ug_m3),
            single_pass_time_fraction=None if level is None else min(1., pass_s / period),
            # A deliberately optimistic lower limit: full continuous coverage,
            # independent noise, stationary correct profile, no drift/bias.
            optimistic_continuous_iid_lod_ug_m3=None if level is None else float(row.detection_limit_ug_m3 * np.sqrt(10 / period)),
            **assessment))
    write("environmental_requirement_assessment.json", rows)
    pd.DataFrame([{**r, "reasons": ";".join(r["reasons"])} for r in rows]).to_csv(OUT / "environmental_requirement_assessment.csv", index=False)
    return rows


def pm_information():
    data = np.load(PREVIOUS / "physics_order4.npz")
    channel = np.load(PREVIOUS / "multiband_reference_channel.npz")
    mask = channel["sensing_mask"]
    names = json.loads((PREVIOUS / "physics_manifest.json").read_text())["gas_names"]
    gas = natural_mass_design(data["gas"][:256], names, [MOLAR_MASS_G_MOL[n] for n in names])[mask]
    pm = data["pm"][:256][mask]
    background = data["background_db"][:256][mask]
    variance = 2 * (10 / np.log(10)) ** 2 / (30000 * channel["snr"][mask])
    nuisance = np.column_stack((np.ones(mask.sum()), background, gas))
    projected = projected_design(pm, nuisance, np.diag(variance))
    cov = covariance_from_information_rows(projected)
    corr = float(projected[:, 0] @ projected[:, 1] / np.prod(np.linalg.norm(projected, axis=0)))
    _, singular, vh = np.linalg.svd(projected, full_matrices=False)
    truth = np.array([49., 41.])
    direction = vh[-1]
    # Choose a nonnegative alternative at the nearest forward boundary along
    # the weak direction. This is a diagnostic pair, not a new PM label.
    if not np.any(direction < 0):
        direction = -direction
    distance = min(-truth[direction < 0] / direction[direction < 0])
    alternative = truth + .95 * distance * direction
    delta = alternative - truth
    separation = float(np.linalg.norm(projected @ delta))
    oracle = 1 / np.linalg.norm(projected, axis=0)
    # Oracle row above still allows gas/background nuisance but fixes the
    # OTHER PM mode. It does not assume all backgrounds are known.
    rows = [dict(case="THz joint only", auxiliary_sigma_ug_m3=None,
                 fine_std_ug_m3=float(np.sqrt(cov[0, 0])), coarse_std_ug_m3=float(np.sqrt(cov[1, 1])),
                 total_std_ug_m3=float(np.sqrt(np.ones(2) @ cov @ np.ones(2))),
                 source="Conditional THz model with unknown gas/background")]
    for sigma in [1., 5., 10.]:
        for tag, extra in [("independent fine measurement", [[1 / sigma, 0]]),
                           ("independent total measurement", [[1 / sigma, 1 / sigma]]),
                           ("independent fine and total measurements", [[1 / sigma, 0], [1 / sigma, 1 / sigma]])]:
            augmented = covariance_from_information_rows(np.vstack((projected, extra)))
            rows.append(dict(case=tag, auxiliary_sigma_ug_m3=sigma,
                fine_std_ug_m3=float(np.sqrt(augmented[0, 0])), coarse_std_ug_m3=float(np.sqrt(augmented[1, 1])),
                total_std_ug_m3=float(np.sqrt(np.ones(2) @ augmented @ np.ones(2))),
                source="Hypothetical independent calibrated mass observation; requirement sensitivity, not acquired data"))
    pd.DataFrame(rows).to_csv(OUT / "pm_auxiliary_requirements.csv", index=False)
    summary = dict(projected_fine_coarse_correlation=corr, physical_singular_values=singular.tolist(),
        fine_and_coarse_std_ug_m3=np.sqrt(np.diag(cov)).tolist(), other_pm_known_std_ug_m3=oracle.tolist(),
        truth_ug_m3=truth.tolist(), alternative_ug_m3=alternative.tolist(),
        optimized_nuisance_separation_in_noise_sd=separation, gaussian_kl_divergence=separation ** 2 / 2,
        gaussian_optimal_equal_prior_error=float(__import__("scipy").stats.norm.cdf(-separation / 2)),
        assumption="10 s broad reference, zero residual and bias, assumed particle constants; best nuisance adjustment allowed",
        implication="Additional constraints can supply information, but improvement supplied by external mass observations is not THz retrieval")
    write("pm_information_diagnosis.json", summary)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), layout="constrained")
    f = channel["frequency_ghz"][mask]
    axes[0].plot(f, projected[:, 0] / np.linalg.norm(projected[:, 0]), label="Fine")
    axes[0].plot(f, projected[:, 1] / np.linalg.norm(projected[:, 1]), "--", label="Coarse")
    axes[0].set(xlabel="Frequency (GHz)", ylabel="Normalized projected response", title="PM signatures after nuisance removal")
    axes[0].legend()
    labels = ["Joint THz", "Other PM\nknown", "+fine & total\n5 µg/m³ noise"]
    chosen = next(r for r in rows if r["case"] == "independent fine and total measurements" and r["auxiliary_sigma_ug_m3"] == 5)
    axes[1].bar(np.arange(3) - .16, [np.sqrt(cov[0, 0]), oracle[0], chosen["fine_std_ug_m3"]], width=.32, label="Fine")
    axes[1].bar(np.arange(3) + .16, [np.sqrt(cov[1, 1]), oracle[1], chosen["coarse_std_ug_m3"]], width=.32, label="Coarse")
    axes[1].set(yscale="log", xticks=np.arange(3), xticklabels=labels, ylabel="Conditional standard error (µg/m³)", title="Where additional information comes from")
    axes[1].legend()
    for ax in axes:
        ax.grid(axis="y", alpha=.2)
    fig.savefig(OUT / "pm_information_diagnosis.png", dpi=180)
    fig.savefig(OUT / "pm_information_diagnosis.svg")
    plt.close(fig)
    return summary


def radio():
    config = LEOLinkBudgetConfig(**json.loads((ROOT / "results/tables/physical_feasibility_config.json").read_text())["reference_link"])
    plan = OFDMPlan((73.5,))
    saved = np.load(PREVIOUS / "eband_73p5GHz_channel.npz")
    snr = saved["snr"]
    base_rate = float(np.log2(1 + snr).sum())
    def ratio(cfo, phase):
        return float(impaired_spectral_efficiency(snr, ofdm_coherent_fraction(cfo, plan.spacing_hz, phase)).sum() / base_rate)
    cfo_limit = brentq(lambda cfo: ratio(cfo, 0) - .99, 0, plan.spacing_hz / 2)
    phase_limit = brentq(lambda phase: ratio(0, phase) - .99, 0, 1)
    frame_results = [ofdm_qpsk_control(snr, normalized_cfo=cfo) for cfo in [0., .01, .1]]
    for record in frame_results:
        record["uncoded_payload_rate_bps"] = record["payload_bits"] / (plan.symbol_duration_s * plan.frame_symbols)
        record["incremental_pilot_reuse_loss_pct"] = 0.
    write("ofdm_waveform_controls.json", frame_results)
    standard = StandardAtmosphere()
    edges = np.unique(np.r_[np.arange(0, 20001, 100), np.arange(20500, 100001, 500)])
    total = 10 ** ((config.tx_power_dbm - 30) / 10)
    pass_duration = maximum_zenith_pass_s(45)
    earth = config.earth_radius_km * 1000
    radius = earth + config.satellite_altitude_km * 1000
    omega = np.sqrt(3.986004418e14 / radius ** 3)
    samples = []
    for time in np.linspace(-pass_duration / 2, pass_duration / 2, 17):
        angle = omega * abs(time)
        distance = np.sqrt(radius ** 2 + earth ** 2 - 2 * earth * radius * np.cos(angle))
        elevation = np.rad2deg(np.arcsin((radius * np.cos(angle) - earth) / distance))
        elevation = float(np.clip(elevation, 45, 90))
        ray = satellite_slant_quadrature(standard, elevation, top_altitude_m=100000, order=2, layer_edges_m=edges)
        t, p, w, _ = standard.state(ray.altitude_m)
        # Chunk molecular background evaluation to bound temporary memory.
        layers = []
        for start in range(0, len(t), 96):
            sl = slice(start, start + 96)
            gamma = specific_attenuation(plan.frequency_ghz, t[sl], p[sl], w[sl] * 1e6 * Boltzmann * t[sl])["total"]
            layers.append(gamma * ray.path_weights_m[sl, None] / 1000)
        layers = np.vstack(layers)
        sky = downwelling_brightness_k(plan.frequency_ghz, t, layers)
        ch = physical_channel_gain(plan.frequency_ghz, layers.sum(axis=0), sky, config, elevation)
        power = waterfill_power(ch["gain_per_watt"], total)
        radial_v = earth * radius * omega * np.sin(omega * time) / distance
        samples.append(dict(time_from_zenith_s=float(time), elevation_deg=elevation, range_km=distance / 1000,
            central_doppler_hz=-radial_v * 73.5e9 / speed_of_light,
            modeled_rate_bps=plan.net_rate_bps(ch["gain_per_watt"], power), incremental_sensing_loss_pct=0.,
            pilot_reuse="Identical existing pilots/power under same channel; instantaneous waterfilling assumes tracking"))
    pd.DataFrame(samples).to_csv(OUT / "eband_moving_pass.csv", index=False)
    times = np.array([r["time_from_zenith_s"] for r in samples])
    rates = np.array([r["modeled_rate_bps"] for r in samples])
    doppler = np.array([r["central_doppler_hz"] for r in samples])
    summary = dict(plan=asdict(plan), occupied_band_edges_ghz=[73.5 - .128, 73.5 + .128],
        band_selection="71-76 GHz space-to-Earth reference; no licensing or coordination determination",
        decision="Communication engineering reference retained; current E-band joint VOC/PM sensing rejected",
        hardware_reference="VDI WR12 VNA extenders cover 60-90 GHz; laboratory measurement equipment, not a flight modem",
        hardware_source="https://vadiodes.com/wp-content/uploads/2012/01/VDI-956_VNA-X_Typical_Performance_2022.03.17.pdf",
        hardware_spec_magnitude_stability_db=.1, hardware_spec_phase_stability_deg=1.5,
        hardware_spec_scope="Typical WR12 values; one hour after warm-up with ideal cables and stable laboratory environment; not a measured stochastic covariance",
        one_percent_rate_loss_cfo_limit_hz=float(cfo_limit), one_percent_rate_loss_phase_rms_rad=float(phase_limit),
        limits_scope="Separate one-impairment-at-a-time conditional limits, not a jointly allocated error budget",
        pass_duration_s=pass_duration, pass_average_rate_bps=float(np.trapezoid(rates, times) / pass_duration),
        pass_information_bits=float(np.trapezoid(rates, times)),
        maximum_sampled_absolute_doppler_hz=float(np.max(np.abs(doppler))),
        maximum_sampled_absolute_doppler_rate_hz_s=float(np.max(np.abs(np.gradient(doppler, times)))),
        waveform_scope="Uncoded QPSK control; Shannon rate is separate and not demonstrated modem throughput",
        measured_hardware_validation=False,
        remaining=["Measured amplitude/phase response and drift", "Acquisition/phase tracking during a real pass",
                   "FEC and target BER/availability", "Rain/cloud losses", "Actual spectrum coordination",
                   "A sensing band design with useful VOC/PM information"])
    write("practical_radio_assessment.json", summary)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.3), layout="constrained")
    axes[0].plot(times, rates / 1e6, "o-")
    axes[0].set(xlabel="Seconds from zenith", ylabel="Modeled information rate (Mbit/s)", title="Ideal 550 km overhead E-band pass")
    axes[1].plot(times, doppler / 1e6, "o-")
    axes[1].set(xlabel="Seconds from zenith", ylabel="Carrier Doppler (MHz)", title="Tracking required before pilot reuse")
    for ax in axes:
        ax.grid(alpha=.2)
    fig.savefig(OUT / "eband_moving_pass.png", dpi=180)
    fig.savefig(OUT / "eband_moving_pass.svg")
    plt.close(fig)
    return summary


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    requirements = standards()
    pm = pm_information()
    print("Standards and PM diagnosis completed", flush=True)
    radio_result = radio()
    write("analysis_summary.json", dict(requirement_rows=len(requirements), pm=pm, radio=radio_result))
    print(json.dumps(dict(requirement_rows=len(requirements), pm=pm, radio=radio_result), indent=2))
