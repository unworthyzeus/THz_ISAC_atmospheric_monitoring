"""Optimize conceptual THz sensing probes under a fixed total power budget.

The candidate spectra are built from the real processed HITRAN line table and
the atmospheric state is fixed from real UCI meteorology. Received attenuation
is still modeled rather than measured. The script compares evenly spaced and
physics only D optimal frequency placement, then tests continuous power
allocation with the full pilot variance model.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.estimation_bounds import (  # noqa: E402
    gas_detection_floor_ppm,
    linear_attenuation_crb,
)
from thz_isac.link_budget import compute_leo_link_budget  # noqa: E402
from thz_isac.physical_spectroscopy import (  # noqa: E402
    MOLAR_MASS_G_MOL,
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
)
from thz_isac.probe_design import (  # noqa: E402
    select_d_optimal_indices,
    uniform_probe_indices,
)

from run_physical_feasibility import (  # noqa: E402
    GAS_TARGETS,
    WHO_AVERAGING_PERIOD,
    WHO_GUIDELINES_UG_M3,
    baseline_link_config,
    normalize_nuisance_columns,
    safe_observation_variance,
)


CANDIDATE_COUNT = 1_024
TONE_COUNTS = (16, 32, 64, 128, 256)
POWER_ALLOCATION_TONE_COUNT = 32
POWER_MINIMUM_EQUAL_FRACTION = 1.0e-3


@dataclass(frozen=True)
class Scenario:
    """One declared link and observation setting."""

    name: str
    elevation_deg: float
    n_pilots: int
    residual_error_std_db: float
    tx_power_dbm: float


SCENARIOS = (
    Scenario("reference", 45.0, 30, 0.63, 23.0),
    Scenario("reference_zero_residual", 45.0, 30, 0.0, 23.0),
    Scenario("optimistic_combined", 15.0, 3_000, 0.0, 33.0),
)


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scenario_arrays(design, scenario: Scenario, n_active: int, indices=None):
    """Return selected slant designs, equal power SNR, and observation variance."""

    if indices is None:
        indices = np.arange(len(design.frequency_ghz), dtype=int)
    indices = np.asarray(indices, dtype=int)
    frequency = design.frequency_ghz[indices]
    background = apply_plane_parallel_slant(
        design.background_db[indices], scenario.elevation_deg
    )
    gas = apply_plane_parallel_slant(
        design.gas_db_per_ug_m3[indices], scenario.elevation_deg
    )
    pm = apply_plane_parallel_slant(
        design.pm_db_per_ug_m3[indices], scenario.elevation_deg
    )
    config = replace(
        baseline_link_config(n_active),
        tx_power_dbm=scenario.tx_power_dbm,
    )
    link = compute_leo_link_budget(
        frequency,
        scenario.elevation_deg,
        config,
        atmospheric_loss_db=background,
    )
    snr_db = link.snr_db[0]
    variance = safe_observation_variance(
        snr_db,
        scenario.n_pilots,
        scenario.residual_error_std_db,
    )
    return frequency, background, gas, pm, snr_db, variance


def selection_design(background, gas, pm) -> np.ndarray:
    """Return gas and nuisance columns for parameter balanced selection."""

    nuisance = normalize_nuisance_columns(
        np.ones_like(background),
        background,
        pm[:, 0],
        pm[:, 1],
    )
    return np.column_stack([gas, nuisance])


def gas_crb(gas, background, pm, variance):
    """Compute the nuisance aware joint gas CRB."""

    nuisance = normalize_nuisance_columns(
        np.ones_like(background),
        background,
        pm[:, 0],
        pm[:, 1],
    )
    return linear_attenuation_crb(
        gas,
        variance,
        nuisance_design=nuisance,
        rcond=1.0e-12,
    )


def floor_records(
    *,
    scenario: Scenario,
    method: str,
    tone_count: int,
    indices: np.ndarray,
    frequency: np.ndarray,
    background: np.ndarray,
    gas: np.ndarray,
    pm: np.ndarray,
    snr_db: np.ndarray,
    variance: np.ndarray,
    power_optimization_success: bool | None = None,
) -> list[dict[str, object]]:
    """Build one result row per gas."""

    result = gas_crb(gas, background, pm, variance)
    rows = []
    for target_index, target in enumerate(GAS_TARGETS):
        floor = float(result.target_standard_deviation[target_index])
        guideline = WHO_GUIDELINES_UG_M3[target]
        floor_ppm = float(
            gas_detection_floor_ppm(
                floor,
                MOLAR_MASS_G_MOL[target],
                287.55,
                101_040.0,
            )
        )
        rows.append(
            {
                "scenario": scenario.name,
                "method": method,
                "tone_count": tone_count,
                "target": target,
                "detection_floor_1sigma_ug_m3": floor,
                "detection_floor_3sigma_ug_m3": 3.0 * floor,
                "detection_floor_1sigma_ppm": floor_ppm,
                "floor_to_guideline_ratio": floor / guideline,
                "floor_3sigma_to_guideline_ratio": 3.0 * floor / guideline,
                "who_2021_guideline_ug_m3": guideline,
                "who_averaging_period": WHO_AVERAGING_PERIOD[target],
                "identifiable": bool(result.target_identifiable),
                "target_rank": int(result.target_rank),
                "target_condition_number": float(result.target_condition_number),
                "median_snr_db": float(np.median(snr_db)),
                "q05_snr_db": float(np.quantile(snr_db, 0.05)),
                "q95_snr_db": float(np.quantile(snr_db, 0.95)),
                "frequency_min_ghz": float(np.min(frequency)),
                "frequency_max_ghz": float(np.max(frequency)),
                "selected_index_count": int(len(indices)),
                "power_optimization_success": power_optimization_success,
            }
        )
    return rows


def exact_variance_for_power(
    equal_power_snr_db: np.ndarray,
    power_fractions: np.ndarray,
    n_pilots: int,
    residual_error_std_db: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return SNR and variance after reallocating the same total power."""

    fractions = np.asarray(power_fractions, dtype=float)
    n_tones = len(fractions)
    relative_to_equal = np.maximum(fractions * n_tones, np.finfo(float).tiny)
    snr_db = equal_power_snr_db + 10.0 * np.log10(relative_to_equal)
    variance = safe_observation_variance(
        snr_db,
        n_pilots,
        residual_error_std_db,
    )
    return snr_db, variance


def optimize_exact_power(
    gas: np.ndarray,
    background: np.ndarray,
    pm: np.ndarray,
    equal_power_snr_db: np.ndarray,
    scenario: Scenario,
) -> tuple[np.ndarray, dict[str, object]]:
    """Optimize gas D information using the full pilot variance expression."""

    n_tones = len(equal_power_snr_db)
    gas_scales = np.array(
        [WHO_GUIDELINES_UG_M3[target] for target in GAS_TARGETS], dtype=float
    )
    scaled_gas = gas * gas_scales[None, :]
    nuisance = normalize_nuisance_columns(
        np.ones_like(background),
        background,
        pm[:, 0],
        pm[:, 1],
    )

    def objective(fractions: np.ndarray) -> float:
        _, variance = exact_variance_for_power(
            equal_power_snr_db,
            fractions,
            scenario.n_pilots,
            scenario.residual_error_std_db,
        )
        result = linear_attenuation_crb(
            scaled_gas,
            variance,
            nuisance_design=nuisance,
            rcond=1.0e-12,
        )
        information = result.efficient_target_information
        sign, log_determinant = np.linalg.slogdet(information)
        if sign <= 0.0 or not np.isfinite(log_determinant):
            return 1.0e30
        return -float(log_determinant)

    initial = np.full(n_tones, 1.0 / n_tones, dtype=float)
    lower = POWER_MINIMUM_EQUAL_FRACTION / n_tones
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=[(lower, 1.0)] * n_tones,
        constraints={"type": "eq", "fun": lambda values: np.sum(values) - 1.0},
        options={"ftol": 1.0e-10, "maxiter": 500},
    )
    candidate = np.asarray(result.x, dtype=float)
    candidate /= np.sum(candidate)
    initial_objective = objective(initial)
    final_objective = objective(candidate)
    improved = bool(np.isfinite(final_objective) and final_objective < initial_objective)
    accepted = bool(result.success and improved)
    if not accepted:
        candidate = initial
        final_objective = initial_objective
    metadata = {
        "optimizer_success": bool(result.success),
        "accepted": accepted,
        "message": str(result.message),
        "iterations": int(result.nit),
        "initial_negative_logdet": float(initial_objective),
        "final_negative_logdet": float(final_objective),
        "minimum_fraction": float(np.min(candidate)),
        "maximum_fraction": float(np.max(candidate)),
        "effective_tone_count": float(1.0 / np.sum(candidate**2)),
    }
    return candidate, metadata


def residual_requirement_rows(
    design,
    scenario: Scenario,
    indices: np.ndarray,
    method: str,
) -> list[dict[str, object]]:
    """Find residual error thresholds for one and three sigma guideline ratios."""

    _, background, gas, pm, snr_db, _ = scenario_arrays(
        design, scenario, len(indices), indices
    )

    def ratio(target_index: int, residual: float, multiplier: float) -> float:
        variance = safe_observation_variance(snr_db, scenario.n_pilots, residual)
        result = gas_crb(gas, background, pm, variance)
        floor = float(result.target_standard_deviation[target_index])
        return multiplier * floor / WHO_GUIDELINES_UG_M3[GAS_TARGETS[target_index]]

    rows = []
    for target_index, target in enumerate(GAS_TARGETS):
        for multiplier, label in ((1.0, "one_sigma"), (3.0, "three_sigma")):
            zero_ratio = ratio(target_index, 0.0, multiplier)
            upper_ratio = ratio(target_index, 2.0, multiplier)
            if not np.isfinite(zero_ratio) or zero_ratio > 1.0:
                threshold = np.nan
                status = "unattainable_even_at_zero_residual"
            elif upper_ratio <= 1.0:
                threshold = np.nan
                status = "threshold_above_2_db_search_limit"
            else:
                threshold = float(
                    brentq(
                        lambda residual: ratio(target_index, residual, multiplier)
                        - 1.0,
                        0.0,
                        2.0,
                        xtol=1.0e-10,
                    )
                )
                status = "finite_threshold"
            rows.append(
                {
                    "scenario": scenario.name,
                    "method": method,
                    "tone_count": len(indices),
                    "target": target,
                    "criterion": label,
                    "ratio_at_zero_residual": zero_ratio,
                    "ratio_at_2_db_residual": upper_ratio,
                    "maximum_residual_std_db": threshold,
                    "status": status,
                }
            )
    return rows


def save_figures(summary: pd.DataFrame, output_dir: Path) -> None:
    """Save compact result figures."""

    output_dir.mkdir(parents=True, exist_ok=True)
    reference = summary.loc[
        (summary["scenario"] == "reference")
        & summary["method"].isin(["uniform_equal", "d_optimal_equal"])
    ]
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 6.2), sharex=True)
    for axis, target in zip(axes.ravel(), GAS_TARGETS, strict=True):
        target_rows = reference.loc[reference["target"] == target]
        for method, label in (
            ("uniform_equal", "Uniform"),
            ("d_optimal_equal", "D optimal"),
        ):
            subset = target_rows.loc[target_rows["method"] == method]
            axis.plot(
                subset["tone_count"],
                subset["floor_to_guideline_ratio"],
                marker="o",
                label=label,
            )
        axis.axhline(1.0, color="black", linestyle=":", linewidth=1.0)
        axis.set_yscale("log")
        axis.set_title(target)
        axis.grid(True, which="both", alpha=0.25)
    axes[1, 0].set_xlabel("Active probes")
    axes[1, 1].set_xlabel("Active probes")
    axes[0, 0].set_ylabel("One sigma floor / guideline")
    axes[1, 0].set_ylabel("One sigma floor / guideline")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Fixed total power frequency placement")
    fig.tight_layout()
    fig.savefig(output_dir / "probe_optimization_comparison.png", dpi=220)
    plt.close(fig)

    power = summary.loc[
        summary["tone_count"].eq(POWER_ALLOCATION_TONE_COUNT)
        & summary["method"].isin(["d_optimal_equal", "d_optimal_power"])
    ].copy()
    if not power.empty:
        power["label"] = power["scenario"] + " | " + power["method"]
        pivot = power.pivot(index="target", columns="label", values="floor_to_guideline_ratio")
        pivot = pivot.reindex(GAS_TARGETS)
        fig, axis = plt.subplots(figsize=(8.2, 4.2))
        pivot.plot(kind="bar", logy=True, ax=axis)
        axis.axhline(1.0, color="black", linestyle=":", linewidth=1.0)
        axis.set_xlabel("")
        axis.set_ylabel("One sigma floor / guideline")
        axis.set_title("Exact variance power allocation at 32 probes")
        axis.grid(True, axis="y", which="both", alpha=0.25)
        axis.legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(output_dir / "probe_power_allocation.png", dpi=220)
        plt.close(fig)


def main() -> None:
    """Run the complete optimized probe experiment."""

    air_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "air_quality"
        / "beijing_air_quality_clean.csv.gz"
    )
    hitran_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "hitran"
        / "hitran_60_400GHz_lines.csv"
    )
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(air_path, parse_dates=["datetime"])
    hitran = pd.read_csv(hitran_path)
    surface_temperature_k = float(data["temperature_c"].median() + 273.15)
    surface_pressure_pa = float(data["pressure_hpa"].median() * 100.0)
    surface_dew_point_c = float(data["dew_point_c"].median())
    frequency_ghz = np.linspace(60.0, 400.0, CANDIDATE_COUNT)

    print("Building the 1,024 point real HITRAN candidate design.")
    design = build_layered_zenith_attenuation_design(
        hitran,
        frequency_ghz,
        surface_dew_point_c=surface_dew_point_c,
        pollutant_scale_height_m=1_500.0,
        water_scale_height_m=2_000.0,
        pm_scale_height_m=1_000.0,
        n_layers=24,
        top_altitude_m=12_000.0,
        surface_temperature_k=surface_temperature_k,
        surface_pressure_pa=surface_pressure_pa,
        partition_sum_version=2025,
    )

    summary_rows: list[dict[str, object]] = []
    frequency_rows: list[dict[str, object]] = []
    power_rows: list[dict[str, object]] = []
    optimizer_metadata: list[dict[str, object]] = []
    regularization_rows: list[dict[str, object]] = []
    selections: dict[tuple[str, int, str], np.ndarray] = {}

    for scenario in SCENARIOS:
        print(f"Selecting probes for {scenario.name}.")
        for tone_count in TONE_COUNTS:
            _, full_background, full_gas, full_pm, _, full_variance = scenario_arrays(
                design, scenario, tone_count
            )
            joint = selection_design(full_background, full_gas, full_pm)
            method_indices = {
                "uniform_equal": uniform_probe_indices(CANDIDATE_COUNT, tone_count),
                "d_optimal_equal": select_d_optimal_indices(
                    joint,
                    full_variance,
                    tone_count,
                    regularization=1.0e-9,
                ),
            }
            if scenario.name == "reference" and tone_count == 256:
                baseline_indices = method_indices["d_optimal_equal"]
                baseline_set = set(baseline_indices.tolist())
                for regularization in (1.0e-6, 1.0e-9, 1.0e-12):
                    sensitivity_indices = select_d_optimal_indices(
                        joint,
                        full_variance,
                        tone_count,
                        regularization=regularization,
                    )
                    arrays = scenario_arrays(
                        design,
                        scenario,
                        tone_count,
                        sensitivity_indices,
                    )
                    (
                        sensitivity_frequency,
                        sensitivity_background,
                        sensitivity_gas,
                        sensitivity_pm,
                        sensitivity_snr,
                        sensitivity_variance,
                    ) = arrays
                    sensitivity_result = gas_crb(
                        sensitivity_gas,
                        sensitivity_background,
                        sensitivity_pm,
                        sensitivity_variance,
                    )
                    selected_set = set(sensitivity_indices.tolist())
                    union = baseline_set | selected_set
                    jaccard = len(baseline_set & selected_set) / len(union)
                    for target_index, target in enumerate(GAS_TARGETS):
                        floor = float(
                            sensitivity_result.target_standard_deviation[target_index]
                        )
                        regularization_rows.append(
                            {
                                "regularization": regularization,
                                "target": target,
                                "floor_to_guideline_ratio": floor
                                / WHO_GUIDELINES_UG_M3[target],
                                "selected_frequency_jaccard_with_1e_9": jaccard,
                                "frequency_min_ghz": float(
                                    np.min(sensitivity_frequency)
                                ),
                                "frequency_max_ghz": float(
                                    np.max(sensitivity_frequency)
                                ),
                                "median_snr_db": float(
                                    np.median(sensitivity_snr)
                                ),
                            }
                        )
            for method, indices in method_indices.items():
                selections[(scenario.name, tone_count, method)] = indices.copy()
                arrays = scenario_arrays(design, scenario, tone_count, indices)
                frequency, background, gas, pm, snr_db, variance = arrays
                summary_rows.extend(
                    floor_records(
                        scenario=scenario,
                        method=method,
                        tone_count=tone_count,
                        indices=indices,
                        frequency=frequency,
                        background=background,
                        gas=gas,
                        pm=pm,
                        snr_db=snr_db,
                        variance=variance,
                    )
                )
                for rank, index in enumerate(indices, start=1):
                    frequency_rows.append(
                        {
                            "scenario": scenario.name,
                            "method": method,
                            "tone_count": tone_count,
                            "selection_rank": rank,
                            "candidate_index": int(index),
                            "frequency_ghz": float(design.frequency_ghz[index]),
                            "background_attenuation_db": float(background[rank - 1]),
                            "equal_power_snr_db": float(snr_db[rank - 1]),
                        }
                    )

            if tone_count == POWER_ALLOCATION_TONE_COUNT:
                indices = method_indices["d_optimal_equal"]
                arrays = scenario_arrays(design, scenario, tone_count, indices)
                frequency, background, gas, pm, snr_db, _ = arrays
                fractions, metadata = optimize_exact_power(
                    gas, background, pm, snr_db, scenario
                )
                optimized_snr, variance = exact_variance_for_power(
                    snr_db,
                    fractions,
                    scenario.n_pilots,
                    scenario.residual_error_std_db,
                )
                summary_rows.extend(
                    floor_records(
                        scenario=scenario,
                        method="d_optimal_power",
                        tone_count=tone_count,
                        indices=indices,
                        frequency=frequency,
                        background=background,
                        gas=gas,
                        pm=pm,
                        snr_db=optimized_snr,
                        variance=variance,
                        power_optimization_success=bool(metadata["accepted"]),
                    )
                )
                optimizer_metadata.append({"scenario": scenario.name, **metadata})
                for rank, (index, fraction) in enumerate(
                    zip(indices, fractions, strict=True), start=1
                ):
                    power_rows.append(
                        {
                            "scenario": scenario.name,
                            "tone_count": tone_count,
                            "selection_rank": rank,
                            "candidate_index": int(index),
                            "frequency_ghz": float(design.frequency_ghz[index]),
                            "power_fraction": float(fraction),
                            "power_fraction_relative_to_equal": float(
                                fraction * tone_count
                            ),
                            "optimized_snr_db": float(optimized_snr[rank - 1]),
                        }
                    )

    summary = pd.DataFrame(summary_rows)
    uniform = summary.loc[summary["method"] == "uniform_equal", [
        "scenario",
        "tone_count",
        "target",
        "floor_to_guideline_ratio",
    ]].rename(columns={"floor_to_guideline_ratio": "uniform_floor_ratio"})
    summary = summary.merge(uniform, on=["scenario", "tone_count", "target"], how="left")
    summary["gain_over_uniform"] = (
        summary["uniform_floor_ratio"] / summary["floor_to_guideline_ratio"]
    )
    equal_d_optimal = summary.loc[
        summary["method"] == "d_optimal_equal",
        ["scenario", "tone_count", "target", "floor_to_guideline_ratio"],
    ].rename(
        columns={"floor_to_guideline_ratio": "equal_d_optimal_floor_ratio"}
    )
    summary = summary.merge(
        equal_d_optimal,
        on=["scenario", "tone_count", "target"],
        how="left",
    )
    summary["gain_over_equal_d_optimal"] = (
        summary["equal_d_optimal_floor_ratio"]
        / summary["floor_to_guideline_ratio"]
    )

    requirement_rows = []
    for scenario_name in ("reference", "optimistic_combined"):
        scenario = next(item for item in SCENARIOS if item.name == scenario_name)
        indices = selections[(scenario_name, 256, "d_optimal_equal")]
        requirement_rows.extend(
            residual_requirement_rows(design, scenario, indices, "d_optimal_equal")
        )

    summary.to_csv(table_dir / "probe_optimization_summary.csv", index=False)
    pd.DataFrame(frequency_rows).to_csv(
        table_dir / "probe_selected_frequencies.csv", index=False
    )
    pd.DataFrame(power_rows).to_csv(
        table_dir / "probe_power_allocation.csv", index=False
    )
    pd.DataFrame(regularization_rows).to_csv(
        table_dir / "probe_regularization_sensitivity.csv", index=False
    )
    requirements = pd.DataFrame(requirement_rows)
    requirements.to_csv(
        table_dir / "probe_calibration_requirements.csv", index=False
    )
    save_figures(summary, figure_dir)

    manifest = {
        "study_status": "physics only probe optimization with modeled attenuation",
        "inputs": {
            "air_quality_path": str(air_path.resolve()),
            "air_quality_sha256": sha256_file(air_path),
            "hitran_path": str(hitran_path.resolve()),
            "hitran_sha256": sha256_file(hitran_path),
            "uci_rows": len(data),
            "hitran_lines": len(hitran),
        },
        "surface_conditions_from_uci_medians": {
            "temperature_k": surface_temperature_k,
            "pressure_pa": surface_pressure_pa,
            "dew_point_c": surface_dew_point_c,
        },
        "candidate_grid": {
            "minimum_ghz": 60.0,
            "maximum_ghz": 400.0,
            "count": CANDIDATE_COUNT,
            "spacing_ghz": float(frequency_ghz[1] - frequency_ghz[0]),
            "status": "conceptual multiband candidates, not a contiguous allocation",
        },
        "tone_counts": list(TONE_COUNTS),
        "scenarios": [asdict(scenario) for scenario in SCENARIOS],
        "selection": {
            "method": "greedy regularized D optimal selection",
            "design": "four gas columns plus offset, background, and two PM nuisance columns",
            "column_normalization": True,
            "regularization": 1.0e-9,
            "uses_pollution_labels": False,
        },
        "power_allocation": {
            "tone_count": POWER_ALLOCATION_TONE_COUNT,
            "method": "SLSQP maximization of nuisance projected gas log determinant",
            "variance_model": "full pilot expression including the declared residual floor",
            "fixed_total_power": True,
            "minimum_fraction_of_equal_power": POWER_MINIMUM_EQUAL_FRACTION,
            "optimizer_results": optimizer_metadata,
        },
        "known_limitations": [
            "No measured sub THz attenuation is used.",
            "The 1,024 frequencies are conceptual candidates without instrument bandpass or regulatory constraints.",
            "The optimizer assumes exact HITRAN line positions and the declared median atmosphere.",
            "Independent residual errors can overstate the value of adding probes.",
            "Total occupied bandwidth and the count of independent residual samples increase with active probe count.",
            "Power allocation is optimized at 32 tones only and is not a global hardware design.",
            "WHO values are concentration scale comparisons with different averaging periods.",
        ],
    }
    with (table_dir / "probe_optimization_manifest.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, indent=2)

    best = summary.loc[
        summary.groupby(["scenario", "target"])["floor_to_guideline_ratio"].idxmin()
    ]
    print(
        best[
            [
                "scenario",
                "target",
                "method",
                "tone_count",
                "floor_to_guideline_ratio",
                "gain_over_uniform",
            ]
        ].to_string(index=False)
    )
    print("Wrote probe optimization tables and figures.")


if __name__ == "__main__":
    main()
