"""Run a real data conditioned H2O spectroscopy positive control.

The target values and atmospheric state come from the real UCI record, while
the attenuation remains a HITRAN based modeled observation. The experiment
tests whether the same link and CRB pipeline can resolve a strong atmospheric
species when the spectrum contains sufficient information.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.link_budget import compute_leo_link_budget  # noqa: E402
from thz_isac.physical_spectroscopy import (  # noqa: E402
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
)
from thz_isac.positive_control import (  # noqa: E402
    build_h2o_dew_point_sensitivity,
    h2o_positive_control_crb,
)
from thz_isac.probe_design import (  # noqa: E402
    select_d_optimal_indices,
    uniform_probe_indices,
)

from run_physical_feasibility import (  # noqa: E402
    baseline_link_config,
    safe_observation_variance,
)


CANDIDATE_COUNT = 512
TONE_COUNTS = (16, 32, 64, 128, 256)
ELEVATION_DEG = 45.0
N_PILOTS = 30
RESIDUAL_ERROR_STD_DB = 0.63
DEW_POINT_STEP_C = 0.25


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selection_matrix(sensitivity, *, include_background_scale: bool) -> np.ndarray:
    """Return the target and declared nuisance design used for selection."""

    columns = [
        sensitivity.dew_point_sensitivity_db_per_c,
        np.ones(len(sensitivity.frequency_ghz)),
        sensitivity.gas_nuisance_db_per_ug_m3,
        sensitivity.pm_nuisance_db_per_ug_m3,
    ]
    if include_background_scale:
        columns.append(sensitivity.reference_background_db)
    return np.column_stack(columns)


def equal_power_link(sensitivity, tone_count: int, indices=None):
    """Return selected reference background, SNR, and variance."""

    if indices is None:
        indices = np.arange(len(sensitivity.frequency_ghz), dtype=int)
    indices = np.asarray(indices, dtype=int)
    background = sensitivity.reference_background_db[indices]
    link = compute_leo_link_budget(
        sensitivity.frequency_ghz[indices],
        ELEVATION_DEG,
        baseline_link_config(tone_count),
        atmospheric_loss_db=background,
    )
    snr_db = link.snr_db[0]
    variance = safe_observation_variance(
        snr_db,
        N_PILOTS,
        RESIDUAL_ERROR_STD_DB,
    )
    return snr_db, variance


def nuisance_cases() -> tuple[dict[str, object], ...]:
    """Return the declared positive control nuisance settings."""

    return (
        {
            "name": "ideal_target_only",
            "include_offset_nuisance": False,
            "include_background_scale_nuisance": False,
            "include_pollutant_nuisance": False,
            "include_pm_nuisance": False,
        },
        {
            "name": "offset_gas_pm",
            "include_offset_nuisance": True,
            "include_background_scale_nuisance": False,
            "include_pollutant_nuisance": True,
            "include_pm_nuisance": True,
        },
        {
            "name": "offset_gas_pm_background_scale",
            "include_offset_nuisance": True,
            "include_background_scale_nuisance": True,
            "include_pollutant_nuisance": True,
            "include_pm_nuisance": True,
        },
    )


def save_figure(summary: pd.DataFrame, figure_path: Path) -> None:
    """Save the positive control bound comparison."""

    subset = summary.loc[
        summary["nuisance_case"].isin(
            ["offset_gas_pm", "offset_gas_pm_background_scale"]
        )
    ].copy()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
    for axis, nuisance_case in zip(
        axes,
        ("offset_gas_pm", "offset_gas_pm_background_scale"),
        strict=True,
    ):
        case = subset.loc[subset["nuisance_case"] == nuisance_case]
        for method, label in (
            ("uniform", "Uniform"),
            ("d_optimal_default", "D optimal default"),
            ("d_optimal_strict", "D optimal strict"),
        ):
            rows = case.loc[case["method"] == method]
            axis.plot(
                rows["tone_count"],
                rows["one_sigma_floor_c"],
                marker="o",
                label=label,
            )
        axis.axhline(1.0, color="black", linestyle=":", linewidth=1.0)
        axis.set_yscale("log")
        axis.grid(True, which="both", alpha=0.25)
        title = "Offset, gases, and PM"
        if "background_scale" in nuisance_case:
            title += " plus background scale"
        axis.set_title(title)
        axis.set_xlabel("Active probes")
    axes[0].set_ylabel("Local dew point one sigma floor, degrees C")
    axes[0].legend(fontsize=8)
    fig.suptitle("H2O positive control at the reference link")
    fig.tight_layout()
    fig.savefig(figure_path, dpi=220)
    plt.close(fig)


def main() -> None:
    """Run the positive control and write auditable artifacts."""

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
    figure_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(air_path, parse_dates=["datetime"])
    hitran = pd.read_csv(hitran_path)
    split = chronological_timestamp_split(data)
    validate_disjoint_split(split, len(data))
    train = data.iloc[split.train]
    test = data.iloc[split.test]
    reference_dew_point_c = float(train["dew_point_c"].median())
    surface_temperature_k = float(train["temperature_c"].median() + 273.15)
    surface_pressure_pa = float(train["pressure_hpa"].median() * 100.0)
    train_range_c = float(
        train["dew_point_c"].quantile(0.95)
        - train["dew_point_c"].quantile(0.05)
    )
    test_range_c = float(
        test["dew_point_c"].quantile(0.95)
        - test["dew_point_c"].quantile(0.05)
    )
    spectroscopy_options = {
        "pollutant_scale_height_m": 1_500.0,
        "water_scale_height_m": 2_000.0,
        "pm_scale_height_m": 1_000.0,
        "n_layers": 24,
        "top_altitude_m": 12_000.0,
        "partition_sum_version": 2025,
    }
    frequency_ghz = np.linspace(60.0, 400.0, CANDIDATE_COUNT)

    print("Building the real HITRAN H2O finite difference design.")
    sensitivity = build_h2o_dew_point_sensitivity(
        hitran,
        frequency_ghz,
        reference_dew_point_c=reference_dew_point_c,
        surface_temperature_k=surface_temperature_k,
        surface_pressure_pa=surface_pressure_pa,
        dew_point_step_c=DEW_POINT_STEP_C,
        elevation_deg=ELEVATION_DEG,
        spectroscopy_options=spectroscopy_options,
    )
    default_joint = selection_matrix(
        sensitivity, include_background_scale=False
    )
    strict_joint = selection_matrix(
        sensitivity, include_background_scale=True
    )

    rows: list[dict[str, object]] = []
    frequency_rows: list[dict[str, object]] = []
    selections: dict[tuple[int, str], np.ndarray] = {}
    for tone_count in TONE_COUNTS:
        _, full_variance = equal_power_link(sensitivity, tone_count)
        methods = {
            "uniform": uniform_probe_indices(CANDIDATE_COUNT, tone_count),
            "d_optimal_default": select_d_optimal_indices(
                default_joint,
                full_variance,
                tone_count,
                regularization=1.0e-9,
            ),
            "d_optimal_strict": select_d_optimal_indices(
                strict_joint,
                full_variance,
                tone_count,
                regularization=1.0e-9,
            ),
        }
        for method, indices in methods.items():
            selections[(tone_count, method)] = indices.copy()
            snr_db, variance = equal_power_link(sensitivity, tone_count, indices)
            for case in nuisance_cases():
                name = str(case["name"])
                options = {key: value for key, value in case.items() if key != "name"}
                result = h2o_positive_control_crb(
                    sensitivity,
                    variance,
                    selected_indices=indices,
                    **options,
                )
                rows.append(
                    {
                        "method": method,
                        "tone_count": tone_count,
                        "nuisance_case": name,
                        "one_sigma_floor_c": result.one_sigma_floor,
                        "three_sigma_floor_c": result.three_sigma_floor,
                        "one_sigma_to_train_q05_q95_range": result.one_sigma_floor
                        / train_range_c,
                        "one_sigma_to_test_q05_q95_range": result.one_sigma_floor
                        / test_range_c,
                        "identifiable": bool(result.crb.target_identifiable),
                        "target_condition_number": float(
                            result.crb.target_condition_number
                        ),
                        "nuisance_count": int(result.crb.nuisance_count),
                        "median_snr_db": float(np.median(snr_db)),
                        "q05_snr_db": float(np.quantile(snr_db, 0.05)),
                        "q95_snr_db": float(np.quantile(snr_db, 0.95)),
                    }
                )
            for rank, index in enumerate(indices, start=1):
                frequency_rows.append(
                    {
                        "method": method,
                        "tone_count": tone_count,
                        "selection_rank": rank,
                        "candidate_index": int(index),
                        "frequency_ghz": float(sensitivity.frequency_ghz[index]),
                        "dew_point_sensitivity_db_per_c": float(
                            sensitivity.dew_point_sensitivity_db_per_c[index]
                        ),
                        "reference_background_db": float(
                            sensitivity.reference_background_db[index]
                        ),
                        "equal_power_snr_db": float(snr_db[rank - 1]),
                    }
                )

    summary = pd.DataFrame(rows)
    frequency_table = pd.DataFrame(frequency_rows)

    stability_rows = []
    for method, options in (
        (
            "d_optimal_default",
            {
                "include_offset_nuisance": True,
                "include_background_scale_nuisance": False,
                "include_pollutant_nuisance": True,
                "include_pm_nuisance": True,
            },
        ),
        (
            "d_optimal_strict",
            {
                "include_offset_nuisance": True,
                "include_background_scale_nuisance": True,
                "include_pollutant_nuisance": True,
                "include_pm_nuisance": True,
            },
        ),
    ):
        indices = selections[(256, method)]
        _, variance = equal_power_link(sensitivity, 256, indices)
        for rcond in (1.0e-10, 1.0e-12, 1.0e-15):
            result = h2o_positive_control_crb(
                sensitivity,
                variance,
                selected_indices=indices,
                rcond=rcond,
                **options,
            )
            stability_rows.append(
                {
                    "method": method,
                    "rcond": rcond,
                    "one_sigma_floor_c": result.one_sigma_floor,
                    "full_condition_number": result.crb.full_condition_number,
                    "target_condition_number": result.crb.target_condition_number,
                    "target_identifiable": bool(result.crb.target_identifiable),
                }
            )

    print("Checking local CRB scale linearity and paired state transfer.")
    linearity_rows = []
    diagnostic_specs = []
    for method, nuisance_case in (
        ("d_optimal_default", "offset_gas_pm"),
        ("d_optimal_strict", "offset_gas_pm_background_scale"),
    ):
        floor_c = float(
            summary.loc[
                (summary["method"] == method)
                & (summary["tone_count"] == 256)
                & (summary["nuisance_case"] == nuisance_case),
                "one_sigma_floor_c",
            ].iloc[0]
        )
        for sigma_multiple in (-3.0, -1.0, 1.0, 3.0):
            diagnostic_specs.append(
                {
                    "diagnostic_type": "local_fixed_temperature_pressure",
                    "state": f"{sigma_multiple:+g}_sigma",
                    "method": method,
                    "reference_floor_c": floor_c,
                    "sigma_multiple": sigma_multiple,
                    "dew_point_c": reference_dew_point_c
                    + sigma_multiple * floor_c,
                    "surface_temperature_k": surface_temperature_k,
                    "surface_pressure_pa": surface_pressure_pa,
                }
            )

    nearest_count = max(100, int(np.ceil(0.01 * len(train))))
    for quantile_label, quantile in (("train_q05", 0.05), ("train_q95", 0.95)):
        target_dew_point = float(train["dew_point_c"].quantile(quantile))
        nearest = train.loc[
            (train["dew_point_c"] - target_dew_point)
            .abs()
            .nsmallest(nearest_count)
            .index
        ]
        paired_state = {
            "dew_point_c": float(nearest["dew_point_c"].median()),
            "surface_temperature_k": float(
                nearest["temperature_c"].median() + 273.15
            ),
            "surface_pressure_pa": float(
                nearest["pressure_hpa"].median() * 100.0
            ),
        }
        for method in ("d_optimal_default", "d_optimal_strict"):
            diagnostic_specs.append(
                {
                    "diagnostic_type": "paired_real_state_transfer",
                    "state": quantile_label,
                    "method": method,
                    "reference_floor_c": np.nan,
                    "sigma_multiple": np.nan,
                    **paired_state,
                }
            )

    endpoint_cache: dict[tuple[float, float, float], np.ndarray] = {}
    for spec in diagnostic_specs:
        dew_point_c = float(spec["dew_point_c"])
        endpoint_temperature_k = float(spec["surface_temperature_k"])
        endpoint_pressure_pa = float(spec["surface_pressure_pa"])
        cache_key = (
            dew_point_c,
            endpoint_temperature_k,
            endpoint_pressure_pa,
        )
        if cache_key not in endpoint_cache:
            endpoint = build_layered_zenith_attenuation_design(
                hitran,
                frequency_ghz,
                surface_dew_point_c=dew_point_c,
                surface_temperature_k=endpoint_temperature_k,
                surface_pressure_pa=endpoint_pressure_pa,
                **spectroscopy_options,
            )
            endpoint_cache[cache_key] = apply_plane_parallel_slant(
                endpoint.background_db, ELEVATION_DEG
            )
        actual = endpoint_cache[cache_key]
        linear = sensitivity.reference_background_db + (
            sensitivity.dew_point_sensitivity_db_per_c
            * (dew_point_c - reference_dew_point_c)
        )
        actual_change = actual - sensitivity.reference_background_db
        error = linear - actual
        indices = selections[(256, str(spec["method"]))]
        selected_error = error[indices]
        selected_change = actual_change[indices]
        change_rms = float(np.sqrt(np.mean(selected_change**2)))
        error_rms = float(np.sqrt(np.mean(selected_error**2)))
        linearity_rows.append(
            {
                **spec,
                "surface_temperature_c": endpoint_temperature_k - 273.15,
                "surface_pressure_hpa": endpoint_pressure_pa / 100.0,
                "offset_from_reference_c": dew_point_c - reference_dew_point_c,
                "tone_count": len(indices),
                "rms_linearization_or_transfer_error_db": error_rms,
                "peak_linearization_or_transfer_error_db": float(
                    np.max(np.abs(selected_error))
                ),
                "rms_actual_background_change_db": change_rms,
                "relative_rms_error": float(
                    error_rms / change_rms if change_rms > 0.0 else np.nan
                ),
                "rms_error_to_residual_std_ratio": error_rms
                / RESIDUAL_ERROR_STD_DB,
            }
        )

    summary.to_csv(table_dir / "h2o_positive_control_summary.csv", index=False)
    frequency_table.to_csv(
        table_dir / "h2o_positive_control_frequencies.csv", index=False
    )
    pd.DataFrame(linearity_rows).to_csv(
        table_dir / "h2o_positive_control_linearity.csv", index=False
    )
    pd.DataFrame(stability_rows).to_csv(
        table_dir / "h2o_positive_control_numerical_stability.csv", index=False
    )
    save_figure(summary, figure_dir / "h2o_positive_control.png")

    manifest = {
        "study_status": "strong species positive control with modeled attenuation",
        "inputs": {
            "air_quality_path": str(air_path.resolve()),
            "air_quality_sha256": sha256_file(air_path),
            "hitran_path": str(hitran_path.resolve()),
            "hitran_sha256": sha256_file(hitran_path),
            "uci_rows": len(data),
            "hitran_lines": len(hitran),
        },
        "chronological_split": {
            "train_rows": len(split.train),
            "validation_rows": len(split.validation),
            "test_rows": len(split.test),
            "train_end": str(split.train_end),
            "validation_end": str(split.validation_end),
        },
        "training_state": {
            "reference_dew_point_c": reference_dew_point_c,
            "surface_temperature_k": surface_temperature_k,
            "surface_pressure_pa": surface_pressure_pa,
            "train_dew_point_q05_q95_range_c": train_range_c,
            "test_dew_point_q05_q95_range_c": test_range_c,
        },
        "observation": {
            "elevation_deg": ELEVATION_DEG,
            "n_pilots": N_PILOTS,
            "residual_error_std_db": RESIDUAL_ERROR_STD_DB,
            "tone_counts": list(TONE_COUNTS),
            "active_subcarriers_rule": "n_active_subcarriers equals tone_count in each result row",
            "reference_hardware_with_256_tone_example": asdict(
                baseline_link_config(256)
            ),
        },
        "spectroscopy": {
            "candidate_count": CANDIDATE_COUNT,
            "dew_point_step_c": DEW_POINT_STEP_C,
            **spectroscopy_options,
        },
        "interpretation": (
            "Local surface dew point parameterizes an assumed H2O column. "
            "It is not a direct measured column retrieval."
        ),
        "known_limitations": [
            "No measured sub THz attenuation is used.",
            "The water scale height is fixed rather than observed.",
            "The local CRB conditions on training median temperature and pressure.",
            "The diagnostic table separates local linearity from transfer to paired real meteorological states.",
            "The stricter background scale nuisance can absorb part of the H2O response.",
            "Candidate frequencies omit instrument bandpass and regulatory constraints.",
        ],
    }
    with (table_dir / "h2o_positive_control_manifest.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, indent=2)

    print(
        summary.loc[
            (summary["method"].str.startswith("d_optimal"))
            & (summary["tone_count"] == 256),
            [
                "method",
                "nuisance_case",
                "one_sigma_floor_c",
                "three_sigma_floor_c",
                "one_sigma_to_test_q05_q95_range",
            ],
        ].to_string(index=False)
    )
    print("Wrote H2O positive control tables and figure.")


if __name__ == "__main__":
    main()
