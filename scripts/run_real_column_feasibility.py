"""Run a preliminary THz feasibility study with real satellite gas columns.

The target distributions are official ESA CCI monthly CO total column and OMI
NO2 tropospheric column retrievals at the declared Beijing grid cell. The THz
attenuation remains modeled from HITRAN. Column domains and retrieval
uncertainties stay explicit and are never converted back to surface mass
concentrations.
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.column_spectroscopy import (  # noqa: E402
    ColumnDomain,
    GasColumnProfile,
    build_column_attenuation_design,
)
from thz_isac.estimation_bounds import linear_attenuation_crb  # noqa: E402
from thz_isac.link_budget import compute_leo_link_budget  # noqa: E402
from thz_isac.physical_spectroscopy import (  # noqa: E402
    DB_PER_NEPER,
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
    standard_troposphere_profile,
)
from thz_isac.probe_design import (  # noqa: E402
    select_d_optimal_indices,
    uniform_probe_indices,
)

from run_physical_feasibility import (  # noqa: E402
    baseline_link_config,
    normalize_nuisance_columns,
    safe_observation_variance,
)


CANDIDATE_COUNT = 512
TONE_COUNTS = (64, 128, 256)
ATMOSPHERE_TOP_M = 20_000.0
N_LAYERS = 40
CO_REFERENCE_SCALE_HEIGHT_M = 8_000.0
NO2_SCALE_HEIGHT_M = 1_500.0

TARGETS = ("CO_total_column", "NO2_tropospheric_column")
COLUMN_FIELDS = {
    "CO_total_column": "co_total_column_day_molecules_cm2",
    "NO2_tropospheric_column": "no2_tropospheric_column_molec_cm2",
}
UNCERTAINTY_FIELDS = {
    "CO_total_column": "co_total_column_uncertainty_day_molecules_cm2",
    "NO2_tropospheric_column": "no2_total_uncertainty_molec_cm2",
}


@dataclass(frozen=True)
class Scenario:
    """One declared column sensing scenario."""

    name: str
    elevation_deg: float
    n_pilots: int
    residual_error_std_db: float
    tx_power_dbm: float


SCENARIOS = (
    Scenario("reference", 45.0, 30, 0.63, 23.0),
    Scenario("optimistic_combined", 15.0, 3_000, 0.0, 33.0),
)


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_statistics(columns: pd.DataFrame) -> pd.DataFrame:
    """Summarize real column spread and reported retrieval uncertainty."""

    rows = []
    for target in TARGETS:
        values = columns[COLUMN_FIELDS[target]].to_numpy(dtype=float)
        uncertainty = columns[UNCERTAINTY_FIELDS[target]].to_numpy(dtype=float)
        q05 = float(np.quantile(values, 0.05))
        q95 = float(np.quantile(values, 0.95))
        median = float(np.median(values))
        median_uncertainty = float(np.median(uncertainty))
        rows.append(
            {
                "target": target,
                "column_domain": (
                    "total_column"
                    if target == "CO_total_column"
                    else "tropospheric_column"
                ),
                "unit": "molecules_cm2",
                "month_count": len(values),
                "minimum": float(np.min(values)),
                "q05": q05,
                "median": median,
                "q95": q95,
                "maximum": float(np.max(values)),
                "q05_q95_range": q95 - q05,
                "median_reported_uncertainty": median_uncertainty,
                "median_reported_uncertainty_to_column": median_uncertainty
                / median,
                "median_reported_uncertainty_to_q05_q95_range": median_uncertainty
                / (q95 - q05),
            }
        )
    return pd.DataFrame(rows)


def scenario_arrays(
    frequency_ghz: np.ndarray,
    background_zenith_db: np.ndarray,
    target_zenith_design: np.ndarray,
    nuisance_zenith_design: np.ndarray,
    scenario: Scenario,
    tone_count: int,
    indices=None,
):
    """Return selected slant columns, SNR, and variance."""

    if indices is None:
        indices = np.arange(len(frequency_ghz), dtype=int)
    indices = np.asarray(indices, dtype=int)
    frequency = frequency_ghz[indices]
    background = apply_plane_parallel_slant(
        background_zenith_db[indices], scenario.elevation_deg
    )
    target = apply_plane_parallel_slant(
        target_zenith_design[indices], scenario.elevation_deg
    )
    nuisance_physics = apply_plane_parallel_slant(
        nuisance_zenith_design[indices], scenario.elevation_deg
    )
    link = compute_leo_link_budget(
        frequency,
        scenario.elevation_deg,
        replace(
            baseline_link_config(tone_count),
            tx_power_dbm=scenario.tx_power_dbm,
        ),
        atmospheric_loss_db=background,
    )
    snr_db = link.snr_db[0]
    variance = safe_observation_variance(
        snr_db,
        scenario.n_pilots,
        scenario.residual_error_std_db,
    )
    return frequency, background, target, nuisance_physics, snr_db, variance


def nuisance_basis(background, nuisance_physics) -> np.ndarray:
    """Return the declared column retrieval nuisance span."""

    columns = [np.ones_like(background), background]
    columns.extend(
        nuisance_physics[:, index]
        for index in range(nuisance_physics.shape[1])
    )
    return normalize_nuisance_columns(*columns)


def target_crb(target, background, nuisance_physics, variance):
    """Return a joint CO and NO2 column CRB."""

    return linear_attenuation_crb(
        target,
        variance,
        nuisance_design=nuisance_basis(background, nuisance_physics),
        rcond=1.0e-12,
    )


def selection_design(target, background, nuisance_physics) -> np.ndarray:
    """Return a unit balanced target and nuisance selection matrix."""

    return np.column_stack(
        [target, nuisance_basis(background, nuisance_physics)]
    )


def save_figure(floors: pd.DataFrame, output_path: Path) -> None:
    """Save column floor to real spread ratios."""

    subset = floors.loc[
        (floors["tone_count"] == 256)
        & (floors["nuisance_case"] == "declared_nuisance")
    ].copy()
    subset["label"] = subset["scenario"] + " | " + subset["method"]
    pivot = subset.pivot(
        index="target",
        columns="label",
        values="floor_to_real_q05_q95_range",
    ).reindex(TARGETS)
    fig, axis = plt.subplots(figsize=(7.8, 4.1))
    pivot.plot(kind="bar", logy=True, ax=axis)
    axis.axhline(1.0, color="black", linestyle=":", linewidth=1.0)
    axis.set_xlabel("")
    axis.set_ylabel("One sigma floor / real Q05 to Q95 range")
    axis.set_title("Real satellite column feasibility")
    axis.grid(True, axis="y", which="both", alpha=0.25)
    axis.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def main() -> None:
    """Run the preliminary real column feasibility experiment."""

    column_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "columns"
        / "beijing_column_series_2013.csv"
    )
    column_manifest_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "columns"
        / "beijing_column_series_2013_manifest.json"
    )
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

    columns = pd.read_csv(column_path)
    if not (
        columns["co_status"].eq("retrieved").all()
        and columns["no2_status"].eq("retrieved").all()
    ):
        raise ValueError("The real column series contains failed product months.")
    air = pd.read_csv(air_path, parse_dates=["datetime"])
    hitran = pd.read_csv(hitran_path)
    period_air = air.loc[
        (air["datetime"] >= "2013-03-01")
        & (air["datetime"] < "2014-01-01")
    ]
    surface_temperature_k = float(period_air["temperature_c"].median() + 273.15)
    surface_pressure_pa = float(period_air["pressure_hpa"].median() * 100.0)
    surface_dew_point_c = float(period_air["dew_point_c"].median())
    frequency_ghz = np.linspace(60.0, 400.0, CANDIDATE_COUNT)
    atmosphere = standard_troposphere_profile(
        n_layers=N_LAYERS,
        top_altitude_m=ATMOSPHERE_TOP_M,
        surface_temperature_k=surface_temperature_k,
        surface_pressure_pa=surface_pressure_pa,
    )

    print("Building domain aware real column HITRAN designs.")
    column_design = build_column_attenuation_design(
        hitran,
        frequency_ghz,
        (
            GasColumnProfile(
                "CO",
                ColumnDomain.TOTAL_COLUMN,
                scale_height_m=CO_REFERENCE_SCALE_HEIGHT_M,
            ),
            GasColumnProfile(
                "NO2",
                ColumnDomain.TROPOSPHERIC_COLUMN,
                scale_height_m=NO2_SCALE_HEIGHT_M,
            ),
        ),
        atmosphere=atmosphere,
        partition_sum_version=2025,
    )
    background_design = build_layered_zenith_attenuation_design(
        hitran,
        frequency_ghz,
        surface_dew_point_c=surface_dew_point_c,
        pollutant_scale_height_m=1_500.0,
        water_scale_height_m=2_000.0,
        pm_scale_height_m=1_000.0,
        n_layers=N_LAYERS,
        top_altitude_m=ATMOSPHERE_TOP_M,
        surface_temperature_k=surface_temperature_k,
        surface_pressure_pa=surface_pressure_pa,
        partition_sum_version=2025,
    )
    target_zenith = column_design.attenuation_db_per_molecule_cm2
    nuisance_zenith = np.column_stack(
        [
            background_design.gas_db_per_ug_m3[:, 1],
            background_design.gas_db_per_ug_m3[:, 2],
            background_design.pm_db_per_ug_m3,
        ]
    )

    statistics = dataset_statistics(columns)
    statistic_lookup = statistics.set_index("target")
    floor_rows: list[dict[str, object]] = []
    frequency_rows: list[dict[str, object]] = []
    selections: dict[tuple[str, int, str], np.ndarray] = {}
    for scenario in SCENARIOS:
        for tone_count in TONE_COUNTS:
            full_arrays = scenario_arrays(
                frequency_ghz,
                background_design.background_db,
                target_zenith,
                nuisance_zenith,
                scenario,
                tone_count,
            )
            (
                _,
                full_background,
                full_target,
                full_nuisance,
                _,
                full_variance,
            ) = full_arrays
            joint = selection_design(
                full_target, full_background, full_nuisance
            )
            methods = {
                "uniform": uniform_probe_indices(CANDIDATE_COUNT, tone_count),
                "d_optimal": select_d_optimal_indices(
                    joint,
                    full_variance,
                    tone_count,
                    regularization=1.0e-9,
                ),
            }
            for method, indices in methods.items():
                selections[(scenario.name, tone_count, method)] = indices.copy()
                arrays = scenario_arrays(
                    frequency_ghz,
                    background_design.background_db,
                    target_zenith,
                    nuisance_zenith,
                    scenario,
                    tone_count,
                    indices,
                )
                frequency, background, target, nuisance, snr_db, variance = arrays
                results = {
                    "ideal_no_nuisance": linear_attenuation_crb(
                        target,
                        variance,
                        rcond=1.0e-12,
                    ),
                    "declared_nuisance": target_crb(
                        target, background, nuisance, variance
                    ),
                }
                for nuisance_case, result in results.items():
                    for target_index, target_name in enumerate(TARGETS):
                        floor = float(
                            result.target_standard_deviation[target_index]
                        )
                        real_range = float(
                            statistic_lookup.loc[target_name, "q05_q95_range"]
                        )
                        retrieval_uncertainty = float(
                            statistic_lookup.loc[
                                target_name, "median_reported_uncertainty"
                            ]
                        )
                        real_median = float(
                            statistic_lookup.loc[target_name, "median"]
                        )
                        floor_rows.append(
                            {
                                "scenario": scenario.name,
                                "method": method,
                                "tone_count": tone_count,
                                "nuisance_case": nuisance_case,
                                "target": target_name,
                                "column_domain": statistic_lookup.loc[
                                    target_name, "column_domain"
                                ],
                                "one_sigma_floor_molecules_cm2": floor,
                                "three_sigma_floor_molecules_cm2": 3.0 * floor,
                                "floor_to_real_q05_q95_range": floor / real_range,
                                "three_sigma_floor_to_real_q05_q95_range": 3.0
                                * floor
                                / real_range,
                                "floor_to_median_retrieval_uncertainty": floor
                                / retrieval_uncertainty,
                                "floor_to_real_median_column": floor / real_median,
                                "identifiable": bool(result.target_identifiable),
                                "target_rank": int(result.target_rank),
                                "target_condition_number": float(
                                    result.target_condition_number
                                ),
                                "median_snr_db": float(np.median(snr_db)),
                                "q05_snr_db": float(np.quantile(snr_db, 0.05)),
                                "q95_snr_db": float(np.quantile(snr_db, 0.95)),
                            }
                        )
                for rank, index in enumerate(indices, start=1):
                    frequency_rows.append(
                        {
                            "scenario": scenario.name,
                            "method": method,
                            "tone_count": tone_count,
                            "selection_rank": rank,
                            "candidate_index": int(index),
                            "frequency_ghz": float(frequency[rank - 1]),
                            "background_attenuation_db": float(
                                background[rank - 1]
                            ),
                            "snr_db": float(snr_db[rank - 1]),
                            "co_sensitivity_db_per_molecule_cm2": float(
                                target[rank - 1, 0]
                            ),
                            "no2_sensitivity_db_per_molecule_cm2": float(
                                target[rank - 1, 1]
                            ),
                        }
                    )

    floors = pd.DataFrame(floor_rows)

    print("Sweeping the assumed CO total column scale height.")
    profile_rows = []
    reference = SCENARIOS[0]
    reference_indices = selections[("reference", 256, "d_optimal")]
    co_cross_section = column_design.layer_cross_section_cm2_per_molecule[:, :, 0]
    for scale_height_m in (4_000.0, 8_000.0, 12_000.0):
        log_weights = (
            -atmosphere.altitude_m / scale_height_m
            + np.log(atmosphere.layer_thickness_m)
        )
        weights = np.exp(log_weights - np.max(log_weights))
        weights /= np.sum(weights)
        co_coefficient = DB_PER_NEPER * np.einsum(
            "lf,l->f", co_cross_section, weights
        )
        varied_target = target_zenith.copy()
        varied_target[:, 0] = co_coefficient
        arrays = scenario_arrays(
            frequency_ghz,
            background_design.background_db,
            varied_target,
            nuisance_zenith,
            reference,
            len(reference_indices),
            reference_indices,
        )
        _, background, target, nuisance, _, variance = arrays
        result = target_crb(target, background, nuisance, variance)
        for target_index, target_name in enumerate(TARGETS):
            floor = float(result.target_standard_deviation[target_index])
            real_range = float(
                statistic_lookup.loc[target_name, "q05_q95_range"]
            )
            profile_rows.append(
                {
                    "co_scale_height_m": scale_height_m,
                    "target": target_name,
                    "one_sigma_floor_molecules_cm2": floor,
                    "floor_to_real_q05_q95_range": floor / real_range,
                    "selection": "fixed reference D optimal 256 probes",
                }
            )

    signature_rows = []
    for target_index, target_name in enumerate(TARGETS):
        real_range = float(statistic_lookup.loc[target_name, "q05_q95_range"])
        signature = target_zenith[:, target_index] * real_range
        peak_index = int(np.argmax(signature))
        signature_rows.append(
            {
                "target": target_name,
                "real_q05_q95_range_molecules_cm2": real_range,
                "peak_zenith_attenuation_across_real_range_db": float(
                    signature[peak_index]
                ),
                "rms_zenith_attenuation_across_real_range_db": float(
                    np.sqrt(np.mean(signature**2))
                ),
                "peak_frequency_ghz": float(frequency_ghz[peak_index]),
            }
        )

    statistics.to_csv(table_dir / "real_column_statistics.csv", index=False)
    floors.to_csv(table_dir / "real_column_detection_floors.csv", index=False)
    pd.DataFrame(frequency_rows).to_csv(
        table_dir / "real_column_selected_frequencies.csv", index=False
    )
    pd.DataFrame(profile_rows).to_csv(
        table_dir / "real_column_profile_sensitivity.csv", index=False
    )
    pd.DataFrame(signature_rows).to_csv(
        table_dir / "real_column_signatures.csv", index=False
    )
    save_figure(
        floors, figure_dir / "real_column_detection_floor.png"
    )

    manifest = {
        "study_status": "preliminary real column target feasibility with modeled THz attenuation",
        "inputs": {
            "column_csv": str(column_path.resolve()),
            "column_csv_sha256": sha256_file(column_path),
            "column_manifest": str(column_manifest_path.resolve()),
            "column_manifest_sha256": sha256_file(column_manifest_path),
            "air_quality_path": str(air_path.resolve()),
            "air_quality_sha256": sha256_file(air_path),
            "hitran_path": str(hitran_path.resolve()),
            "hitran_sha256": sha256_file(hitran_path),
            "month_count": len(columns),
        },
        "column_semantics": {
            "CO": "ESA CCI merged IASI and MOPITT daytime total column retrieval",
            "NO2": "ESA CCI OMI tropospheric vertical column retrieval",
            "unit": "molecules per square centimetre",
            "grid_cell": "39.5 degrees north, 116.5 degrees east",
            "status": "retrieval products, not ground truth",
        },
        "atmosphere": {
            "surface_temperature_k": surface_temperature_k,
            "surface_pressure_pa": surface_pressure_pa,
            "surface_dew_point_c": surface_dew_point_c,
            "top_altitude_m": ATMOSPHERE_TOP_M,
            "n_layers": N_LAYERS,
            "co_total_column_scale_height_m": CO_REFERENCE_SCALE_HEIGHT_M,
            "no2_tropospheric_scale_height_m": NO2_SCALE_HEIGHT_M,
        },
        "candidate_count": CANDIDATE_COUNT,
        "tone_counts": list(TONE_COUNTS),
        "scenarios": [asdict(scenario) for scenario in SCENARIOS],
        "nuisance": [
            "additive offset",
            "full atmospheric background scale",
            "surface O3 profile",
            "surface SO2 profile",
            "fine PM mode",
            "coarse PM mode",
        ],
        "known_limitations": [
            "Only ten monthly retrievals from March through December 2013 are used.",
            "The 1 degree grid cell does not represent individual UCI stations.",
            "Satellite values are retrievals with uncertainty and prior dependence.",
            "The CO total column is normalized into the supported 0 to 20 km model domain, which is an optimistic truncation.",
            "The CO vertical profile is assumed and only swept by scale height.",
            "The standard atmosphere above the tropopause is simplified.",
            "No measured sub THz attenuation is used.",
            "Candidate frequencies omit instrument and regulatory constraints.",
        ],
    }
    with (table_dir / "real_column_feasibility_manifest.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(manifest, handle, indent=2)

    print(
        floors.loc[
            (floors["tone_count"] == 256)
            & (floors["nuisance_case"] == "declared_nuisance"),
            [
                "scenario",
                "method",
                "target",
                "floor_to_real_q05_q95_range",
                "floor_to_median_retrieval_uncertainty",
            ],
        ].to_string(index=False)
    )
    print("Wrote preliminary real column feasibility artifacts.")


if __name__ == "__main__":
    main()
