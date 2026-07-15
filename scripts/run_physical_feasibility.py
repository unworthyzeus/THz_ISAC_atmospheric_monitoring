"""Run the physical detectability and held out estimation study.

The spectroscopic coefficients come from the processed HITRAN line table and
the concentration distribution comes from the complete case UCI Beijing air
quality table. The received attenuation observations remain simulated because
no paired sub THz CSI and pollution field dataset is available in the project.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.estimation_bounds import (  # noqa: E402
    gas_detection_floor_ppm,
    linear_attenuation_crb,
    pilot_averaged_attenuation_variance_from_snr_db,
)
from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.link_budget import (  # noqa: E402
    LEOLinkBudgetConfig,
    compute_leo_link_budget,
)
from thz_isac.physical_spectroscopy import (  # noqa: E402
    MOLAR_MASS_G_MOL,
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
)


GAS_TARGETS = ("CO", "O3", "SO2", "NO2")
REPORT_TARGETS = ("CO", "O3", "SO2", "NO2", "PM2.5", "PM10")
AIR_COLUMNS = {
    "CO": "CO_ug_m3",
    "O3": "O3_ug_m3",
    "SO2": "SO2_ug_m3",
    "NO2": "NO2_ug_m3",
    "PM2.5": "PM2_5_ug_m3",
    "PM10": "PM10_ug_m3",
}

# WHO 2021 air quality guideline levels. They are health guidelines, not legal
# compliance limits. Averaging periods differ and are retained in the table.
WHO_GUIDELINES_UG_M3 = {
    "CO": 4_000.0,
    "O3": 100.0,
    "SO2": 40.0,
    "NO2": 25.0,
    "PM2.5": 15.0,
    "PM10": 45.0,
}
WHO_AVERAGING_PERIOD = {
    "CO": "24 h",
    "O3": "8 h",
    "SO2": "24 h",
    "NO2": "24 h",
    "PM2.5": "24 h",
    "PM10": "24 h",
}

BASE_ELEVATION_DEG = 45.0
BASE_N_PILOTS = 30
BASE_RESIDUAL_ERROR_STD_DB = 0.63
BASE_N_FREQUENCIES = 256
RANDOM_SEED = 20260715


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the HITRAN and UCI physical feasibility experiment."
    )
    parser.add_argument(
        "--air-quality",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "processed"
        / "air_quality"
        / "beijing_air_quality_clean.csv.gz",
    )
    parser.add_argument(
        "--hitran-lines",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "processed"
        / "hitran"
        / "hitran_60_400GHz_lines.csv",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20_000,
        help="Deterministic sample size for the simulated observation benchmark.",
    )
    parser.add_argument(
        "--skip-estimators",
        action="store_true",
        help="Skip the simulated observation estimator benchmark.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_nuisance_columns(*columns: np.ndarray) -> np.ndarray:
    """Return a stable orthonormal basis spanning supplied nuisance columns."""
    matrix = np.column_stack([np.asarray(column, dtype=float) for column in columns])
    norms = np.linalg.norm(matrix, axis=0)
    matrix = matrix[:, norms > 0.0] / norms[norms > 0.0]
    left, singular, _ = np.linalg.svd(matrix, full_matrices=False)
    if singular.size == 0:
        return np.empty((len(columns[0]), 0), dtype=float)
    keep = singular > singular[0] * 1e-10
    return left[:, keep]


def safe_observation_variance(
    snr_db: np.ndarray,
    n_pilots: int,
    residual_error_std_db: float,
) -> np.ndarray:
    """Evaluate pilot variance while assigning negligible weight to opaque tones."""
    clipped_snr = np.clip(np.asarray(snr_db, dtype=float), -150.0, 150.0)
    return pilot_averaged_attenuation_variance_from_snr_db(
        clipped_snr,
        n_pilots,
        residual_error_std_db,
    )


def fixed_pm10_column(pm_design: np.ndarray, fine_fraction: float) -> np.ndarray:
    """Return a fixed composition PM10 attenuation column."""
    return fine_fraction * pm_design[:, 0] + (1.0 - fine_fraction) * pm_design[:, 1]


def target_columns(design, fine_fraction: float) -> dict[str, np.ndarray]:
    """Map report target names to zenith attenuation design columns."""
    columns = {
        gas: design.gas_db_per_ug_m3[:, index]
        for index, gas in enumerate(design.gas_names)
    }
    columns["PM2.5"] = design.pm_db_per_ug_m3[:, 0]
    columns["PM10"] = fixed_pm10_column(design.pm_db_per_ug_m3, fine_fraction)
    return columns


def compute_floor_rows(
    design,
    link_config: LEOLinkBudgetConfig,
    fine_fraction: float,
    *,
    elevation_deg: float,
    n_pilots: int,
    residual_error_std_db: float,
    selected_indices: np.ndarray | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Compute gas joint CRBs and optimistic one mode PM CRBs."""
    if selected_indices is None:
        selected_indices = np.arange(len(design.frequency_ghz))
    selected_indices = np.asarray(selected_indices, dtype=int)
    frequency = design.frequency_ghz[selected_indices]
    background = apply_plane_parallel_slant(
        design.background_db[selected_indices], elevation_deg
    )
    gas = apply_plane_parallel_slant(
        design.gas_db_per_ug_m3[selected_indices, :], elevation_deg
    )
    pm = apply_plane_parallel_slant(
        design.pm_db_per_ug_m3[selected_indices, :], elevation_deg
    )
    link = compute_leo_link_budget(
        frequency,
        elevation_deg,
        link_config,
        atmospheric_loss_db=background,
    )
    snr_db = link.snr_db[0]
    variance = safe_observation_variance(snr_db, n_pilots, residual_error_std_db)

    gas_nuisance = normalize_nuisance_columns(
        np.ones_like(background),
        background,
        pm[:, 0],
        pm[:, 1],
    )
    gas_crb = linear_attenuation_crb(
        gas,
        variance,
        nuisance_design=gas_nuisance,
        rcond=1e-12,
    )

    rows: list[dict[str, object]] = []
    for index, target in enumerate(GAS_TARGETS):
        floor = float(gas_crb.target_standard_deviation[index])
        floor_ppm = float(
            gas_detection_floor_ppm(
                floor,
                MOLAR_MASS_G_MOL[target],
                design.atmosphere.temperature_k[0],
                design.atmosphere.pressure_pa[0],
            )
        )
        rows.append(
            make_floor_row(
                target,
                floor,
                floor_ppm,
                elevation_deg,
                n_pilots,
                residual_error_std_db,
                snr_db,
                gas_crb.target_identifiable,
                gas_crb.target_condition_number,
                "joint gas CRB with background and PM spectral nuisance",
            )
        )

    pm10 = fixed_pm10_column(pm, fine_fraction)
    for target, column, assumption in (
        ("PM2.5", pm[:, 0], "optimistic single fine mode CRB"),
        (
            "PM10",
            pm10,
            f"optimistic fixed composition PM10 CRB, fine fraction {fine_fraction:.4f}",
        ),
    ):
        pm_nuisance = normalize_nuisance_columns(
            np.ones_like(background),
            background,
            *[gas[:, index] for index in range(gas.shape[1])],
        )
        pm_crb = linear_attenuation_crb(
            column[:, None],
            variance,
            nuisance_design=pm_nuisance,
            rcond=1e-12,
        )
        floor = float(pm_crb.target_standard_deviation[0])
        rows.append(
            make_floor_row(
                target,
                floor,
                np.nan,
                elevation_deg,
                n_pilots,
                residual_error_std_db,
                snr_db,
                pm_crb.target_identifiable,
                pm_crb.target_condition_number,
                assumption,
            )
        )

    diagnostics = {
        "slant_range_km": float(link.slant_range_km[0]),
        "snr_median_db": float(np.median(snr_db)),
        "snr_q05_db": float(np.quantile(snr_db, 0.05)),
        "snr_q95_db": float(np.quantile(snr_db, 0.95)),
        "tones_above_5_db": int(np.sum(snr_db > 5.0)),
        "tone_count": int(len(frequency)),
        "gas_target_rank": gas_crb.target_rank,
        "gas_target_count": gas_crb.target_count,
    }
    return rows, diagnostics


def make_floor_row(
    target: str,
    floor_ug_m3: float,
    floor_ppm: float,
    elevation_deg: float,
    n_pilots: int,
    residual_error_std_db: float,
    snr_db: np.ndarray,
    identifiable: bool,
    condition_number: float,
    assumption: str,
) -> dict[str, object]:
    """Build one detection floor result record."""
    guideline = WHO_GUIDELINES_UG_M3[target]
    return {
        "target": target,
        "elevation_deg": elevation_deg,
        "n_pilots": n_pilots,
        "residual_error_std_db": residual_error_std_db,
        "detection_floor_1sigma_ug_m3": floor_ug_m3,
        "detection_floor_1sigma_ppm": floor_ppm,
        "detection_floor_3sigma_ug_m3": 3.0 * floor_ug_m3,
        "detection_floor_3sigma_ppm": 3.0 * floor_ppm,
        "who_2021_guideline_ug_m3": guideline,
        "who_averaging_period": WHO_AVERAGING_PERIOD[target],
        "floor_to_guideline_ratio": floor_ug_m3 / guideline,
        "floor_3sigma_to_guideline_ratio": 3.0 * floor_ug_m3 / guideline,
        "median_snr_db": float(np.median(snr_db)),
        "q05_snr_db": float(np.quantile(snr_db, 0.05)),
        "q95_snr_db": float(np.quantile(snr_db, 0.95)),
        "identifiable": bool(identifiable),
        "condition_number": condition_number,
        "assumption": assumption,
    }


def build_signature_summary(
    data: pd.DataFrame,
    design,
    fine_fraction: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize real concentration quantiles and their physical signatures."""
    columns = target_columns(design, fine_fraction)
    rows = []
    informative_rows = []
    background = apply_plane_parallel_slant(design.background_db, BASE_ELEVATION_DEG)
    base_link = compute_leo_link_budget(
        design.frequency_ghz,
        BASE_ELEVATION_DEG,
        baseline_link_config(BASE_N_FREQUENCIES),
        atmospheric_loss_db=background,
    )
    variance = safe_observation_variance(
        base_link.snr_db[0], BASE_N_PILOTS, BASE_RESIDUAL_ERROR_STD_DB
    )
    for target in REPORT_TARGETS:
        concentration = data[AIR_COLUMNS[target]].to_numpy(dtype=float)
        q95 = float(np.quantile(concentration, 0.95))
        slant_column = apply_plane_parallel_slant(columns[target], BASE_ELEVATION_DEG)
        signature = q95 * slant_column
        peak_index = int(np.argmax(signature))
        rows.append(
            {
                "target": target,
                "uci_q05_ug_m3": float(np.quantile(concentration, 0.05)),
                "uci_median_ug_m3": float(np.median(concentration)),
                "uci_q95_ug_m3": q95,
                "who_2021_guideline_ug_m3": WHO_GUIDELINES_UG_M3[target],
                "q95_peak_excess_attenuation_db_at_45_deg": float(signature[peak_index]),
                "q95_rms_excess_attenuation_db_at_45_deg": float(
                    np.sqrt(np.mean(signature**2))
                ),
                "peak_frequency_ghz": float(design.frequency_ghz[peak_index]),
                "peak_to_residual_error_std_ratio": float(
                    signature[peak_index] / BASE_RESIDUAL_ERROR_STD_DB
                ),
            }
        )
        fisher_contribution = slant_column**2 / variance
        order = np.argsort(fisher_contribution)[::-1][:10]
        total = float(np.sum(fisher_contribution))
        for rank, index in enumerate(order, start=1):
            informative_rows.append(
                {
                    "target": target,
                    "rank": rank,
                    "frequency_ghz": float(design.frequency_ghz[index]),
                    "sensitivity_db_per_ug_m3": float(slant_column[index]),
                    "background_attenuation_db": float(background[index]),
                    "snr_db": float(base_link.snr_db[0, index]),
                    "single_target_fisher_fraction": float(
                        fisher_contribution[index] / total if total > 0.0 else 0.0
                    ),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(informative_rows)


def baseline_link_config(n_active: int) -> LEOLinkBudgetConfig:
    """Return the declared reference link budget configuration."""
    return LEOLinkBudgetConfig(
        satellite_altitude_km=550.0,
        tx_power_dbm=23.0,
        tx_aperture_diameter_m=0.50,
        rx_aperture_diameter_m=0.30,
        subcarrier_bandwidth_hz=1.0e6,
        tx_aperture_efficiency=0.65,
        rx_aperture_efficiency=0.65,
        receiver_noise_figure_db=6.0,
        receiver_noise_temperature_k=290.0,
        implementation_loss_db=5.0,
        n_active_subcarriers=n_active,
    )


def run_sensitivity(design, fine_fraction: float) -> pd.DataFrame:
    """Sweep elevation, pilot count, power, tone count, and residual error."""
    scenarios: list[dict[str, object]] = []
    for value in (15.0, 30.0, 45.0, 60.0, 80.0):
        scenarios.append({"variable": "elevation_deg", "value": value})
    for value in (30, 300, 3_000):
        scenarios.append({"variable": "n_pilots", "value": value})
    for value in (13.0, 23.0, 33.0):
        scenarios.append({"variable": "tx_power_dbm", "value": value})
    for value in (64, 128, 256):
        scenarios.append({"variable": "n_active_tones", "value": value})
    for value in (0.0, 0.10, 0.63):
        scenarios.append({"variable": "residual_error_std_db", "value": value})

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, float]] = set()
    for scenario in scenarios:
        variable = str(scenario["variable"])
        value = float(scenario["value"])
        key = (variable, value)
        if key in seen:
            continue
        seen.add(key)
        elevation = value if variable == "elevation_deg" else BASE_ELEVATION_DEG
        pilots = int(value) if variable == "n_pilots" else BASE_N_PILOTS
        residual_error = (
            value
            if variable == "residual_error_std_db"
            else BASE_RESIDUAL_ERROR_STD_DB
        )
        n_tones = int(value) if variable == "n_active_tones" else BASE_N_FREQUENCIES
        indices = np.linspace(0, BASE_N_FREQUENCIES - 1, n_tones, dtype=int)
        link_config = baseline_link_config(n_tones)
        if variable == "tx_power_dbm":
            link_config = replace(link_config, tx_power_dbm=value)
        floor_rows, _ = compute_floor_rows(
            design,
            link_config,
            fine_fraction,
            elevation_deg=elevation,
            n_pilots=pilots,
            residual_error_std_db=residual_error,
            selected_indices=indices,
        )
        for row in floor_rows:
            row.update(
                {
                    "sensitivity_variable": variable,
                    "sensitivity_value": value,
                    "tone_count": n_tones,
                    "tx_power_dbm": link_config.tx_power_dbm,
                }
            )
            rows.append(row)

    # This combination is deliberately optimistic and is not a deployment
    # recommendation. It prevents one factor at a time results from being
    # misread as a universal impossibility statement.
    optimistic_config = replace(
        baseline_link_config(BASE_N_FREQUENCIES),
        tx_power_dbm=33.0,
    )
    optimistic_rows, _ = compute_floor_rows(
        design,
        optimistic_config,
        fine_fraction,
        elevation_deg=15.0,
        n_pilots=3_000,
        residual_error_std_db=0.0,
    )
    for row in optimistic_rows:
        row.update(
            {
                "sensitivity_variable": "optimistic_combined",
                "sensitivity_value": 1.0,
                "tone_count": BASE_N_FREQUENCIES,
                "tx_power_dbm": optimistic_config.tx_power_dbm,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def regression_metrics(
    truth: np.ndarray,
    prediction: np.ndarray,
    target_names: tuple[str, ...],
    denominators: np.ndarray,
    model: str,
    split: str,
) -> list[dict[str, object]]:
    """Return one record per target for a multivariate prediction."""
    rows = []
    for index, target in enumerate(target_names):
        error = prediction[:, index] - truth[:, index]
        rmse = float(np.sqrt(np.mean(error**2)))
        mae = float(np.mean(np.abs(error)))
        denominator = float(max(denominators[index], np.finfo(float).eps))
        total = float(np.sum((truth[:, index] - np.mean(truth[:, index])) ** 2))
        residual = float(np.sum(error**2))
        rows.append(
            {
                "model": model,
                "split": split,
                "target": target,
                "mae_ug_m3": mae,
                "rmse_ug_m3": rmse,
                "normalized_rmse": rmse / denominator,
                "r2": 1.0 - residual / total if total > 0.0 else np.nan,
                "bias_ug_m3": float(np.mean(error)),
                "negative_prediction_rate": float(np.mean(prediction[:, index] < 0.0)),
            }
        )
    return rows


def ridge_predictions(
    observations: np.ndarray,
    targets: np.ndarray,
    split,
    denominators: np.ndarray,
) -> tuple[np.ndarray, float, pd.DataFrame]:
    """Select Ridge alpha on validation only and return test predictions."""
    scaler = StandardScaler()
    train_x = scaler.fit_transform(observations[split.train])
    validation_x = scaler.transform(observations[split.validation])
    test_x = scaler.transform(observations[split.test])
    rows = []
    best_score = np.inf
    best_alpha = np.nan
    best_model = None
    for alpha in (
        0.01,
        0.1,
        1.0,
        10.0,
        100.0,
        1_000.0,
        10_000.0,
        100_000.0,
        1_000_000.0,
        10_000_000.0,
        100_000_000.0,
    ):
        model = Ridge(alpha=alpha)
        model.fit(train_x, targets[split.train])
        prediction = model.predict(validation_x)
        rmse = np.sqrt(np.mean((prediction - targets[split.validation]) ** 2, axis=0))
        score = float(np.mean(rmse / denominators))
        rows.append({"alpha": alpha, "validation_mean_normalized_rmse": score})
        if score < best_score:
            best_score = score
            best_alpha = alpha
            best_model = model
    assert best_model is not None
    return best_model.predict(test_x), float(best_alpha), pd.DataFrame(rows)


def wls_batch(design: np.ndarray, observations: np.ndarray, variance: np.ndarray) -> np.ndarray:
    """Solve a common design weighted least squares problem for many records."""
    scale = np.sqrt(variance)
    weighted_design = design / scale[:, None]
    weighted_observations = observations / scale[None, :]
    solution, _, _, _ = np.linalg.lstsq(
        weighted_design,
        weighted_observations.T,
        rcond=1e-12,
    )
    return solution.T


def run_estimator_benchmark(
    data: pd.DataFrame,
    design,
    hitran: pd.DataFrame,
    surface_temperature_k: float,
    surface_pressure_pa: float,
    surface_dew_point_c: float,
    sample_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Evaluate estimators on simulated attenuation with real UCI labels."""
    physically_ordered = data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]].copy()
    physically_ordered = physically_ordered.sort_values(["datetime", "station"]).reset_index(drop=True)
    if sample_size < 100 or sample_size > len(physically_ordered):
        raise ValueError("sample_size must be at least 100 and no larger than the usable dataset")
    sample_indices = np.linspace(0, len(physically_ordered) - 1, sample_size, dtype=int)
    sample = physically_ordered.iloc[sample_indices].reset_index(drop=True)

    report_targets = sample[[AIR_COLUMNS[target] for target in REPORT_TARGETS]].to_numpy(float)
    parameter_targets = np.column_stack(
        [
            report_targets[:, :5],
            report_targets[:, 5] - report_targets[:, 4],
        ]
    )
    metadata = sample[["datetime", "station"]].copy()
    split = chronological_timestamp_split(metadata)
    validate_disjoint_split(split, len(sample))

    elevation = BASE_ELEVATION_DEG
    gas_design = apply_plane_parallel_slant(design.gas_db_per_ug_m3, elevation)
    pm_design = apply_plane_parallel_slant(design.pm_db_per_ug_m3, elevation)
    joint_design = np.column_stack([gas_design, pm_design])
    background = apply_plane_parallel_slant(design.background_db, elevation)
    link = compute_leo_link_budget(
        design.frequency_ghz,
        elevation,
        baseline_link_config(BASE_N_FREQUENCIES),
        atmospheric_loss_db=background,
    )
    variance = safe_observation_variance(
        link.snr_db[0], BASE_N_PILOTS, BASE_RESIDUAL_ERROR_STD_DB
    )
    rng = np.random.default_rng(RANDOM_SEED)
    excess = parameter_targets @ joint_design.T
    observations = excess + rng.normal(
        scale=np.sqrt(variance),
        size=excess.shape,
    )

    denominators = np.quantile(report_targets[split.train], 0.95, axis=0) - np.quantile(
        report_targets[split.train], 0.05, axis=0
    )
    metrics: list[dict[str, object]] = []
    train_mean = np.mean(report_targets[split.train], axis=0)
    mean_prediction = np.broadcast_to(train_mean, report_targets[split.test].shape)
    metrics.extend(
        regression_metrics(
            report_targets[split.test],
            mean_prediction,
            REPORT_TARGETS,
            denominators,
            "training period mean",
            "test",
        )
    )

    ridge_prediction, best_alpha, alpha_table = ridge_predictions(
        observations,
        report_targets,
        split,
        denominators,
    )
    metrics.extend(
        regression_metrics(
            report_targets[split.test],
            ridge_prediction,
            REPORT_TARGETS,
            denominators,
            "Ridge selected on validation",
            "test",
        )
    )

    test_observations = observations[split.test]
    joint_parameters = wls_batch(joint_design, test_observations, variance)
    joint_report = np.column_stack(
        [
            joint_parameters[:, :5],
            joint_parameters[:, 4] + joint_parameters[:, 5],
        ]
    )
    metrics.extend(
        regression_metrics(
            report_targets[split.test],
            joint_report,
            REPORT_TARGETS,
            denominators,
            "oracle joint physical WLS",
            "test",
        )
    )

    true_test_pm = parameter_targets[split.test, 4:] @ pm_design.T
    gas_observations = test_observations - true_test_pm
    gas_prediction = wls_batch(gas_design, gas_observations, variance)
    metrics.extend(
        regression_metrics(
            report_targets[split.test, :4],
            gas_prediction,
            GAS_TARGETS,
            denominators[:4],
            "oracle gas WLS with true PM removed",
            "test",
        )
    )

    mismatch_design = build_layered_zenith_attenuation_design(
        hitran,
        design.frequency_ghz,
        surface_dew_point_c=surface_dew_point_c,
        pollutant_scale_height_m=1_200.0,
        water_scale_height_m=2_000.0,
        pm_scale_height_m=1_000.0,
        n_layers=24,
        top_altitude_m=12_000.0,
        surface_temperature_k=surface_temperature_k + 5.0,
        surface_pressure_pa=max(surface_pressure_pa - 2_000.0, 1.0),
        partition_sum_version=2025,
    )
    mismatch_gas = apply_plane_parallel_slant(
        mismatch_design.gas_db_per_ug_m3, elevation
    )
    mismatch_prediction = wls_batch(mismatch_gas, gas_observations, variance)
    metrics.extend(
        regression_metrics(
            report_targets[split.test, :4],
            mismatch_prediction,
            GAS_TARGETS,
            denominators[:4],
            "mismatched gas WLS with true PM removed",
            "test",
        )
    )

    metadata_out = {
        "simulated_observation_rows": len(sample),
        "excluded_pm_ordering_rows": int(len(data) - len(physically_ordered)),
        "train_rows": int(len(split.train)),
        "validation_rows": int(len(split.validation)),
        "test_rows": int(len(split.test)),
        "train_end": str(split.train_end),
        "validation_end": str(split.validation_end),
        "ridge_alpha_selected_on_validation": best_alpha,
        "random_seed": RANDOM_SEED,
        "observation_status": "simulated attenuation generated from HITRAN and real UCI labels",
    }
    return pd.DataFrame(metrics), alpha_table, metadata_out


def save_figures(
    figure_dir: Path,
    data: pd.DataFrame,
    design,
    fine_fraction: float,
    floors: pd.DataFrame,
    sensitivity: pd.DataFrame,
    estimator_metrics: pd.DataFrame | None,
) -> None:
    """Create publication ready result figures."""
    figure_dir.mkdir(parents=True, exist_ok=True)
    columns = target_columns(design, fine_fraction)
    colors = plt.get_cmap("tab10").colors

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True)
    for index, target in enumerate(GAS_TARGETS):
        q95 = float(data[AIR_COLUMNS[target]].quantile(0.95))
        signature = q95 * apply_plane_parallel_slant(columns[target], BASE_ELEVATION_DEG)
        axes[0].semilogy(
            design.frequency_ghz,
            np.maximum(signature, 1e-16),
            label=target,
            color=colors[index],
        )
    axes[0].set_ylabel("Q95 excess attenuation (dB)")
    axes[0].set_title("HITRAN gas signatures at 45 degree elevation")
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(ncol=4, fontsize=8)
    for offset, target in enumerate(("PM2.5", "PM10"), start=4):
        q95 = float(data[AIR_COLUMNS[target]].quantile(0.95))
        signature = q95 * apply_plane_parallel_slant(columns[target], BASE_ELEVATION_DEG)
        axes[1].semilogy(
            design.frequency_ghz,
            np.maximum(signature, 1e-16),
            label=target,
            color=colors[offset],
        )
    axes[1].axhline(
        BASE_RESIDUAL_ERROR_STD_DB,
        color="black",
        linestyle="--",
        linewidth=1.0,
        label="0.63 dB independent residual error standard deviation",
    )
    axes[1].set_xlabel("Frequency (GHz)")
    axes[1].set_ylabel("Q95 excess attenuation (dB)")
    axes[1].set_title("Exploratory Rayleigh PM signatures at 45 degree elevation")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figure_dir / "physical_signatures.png", dpi=220)
    plt.close(fig)

    ordered = floors.set_index("target").loc[list(REPORT_TARGETS)].reset_index()
    fig, ax = plt.subplots(figsize=(7.2, 3.7))
    ratios = ordered["floor_to_guideline_ratio"].to_numpy(float)
    bars = ax.bar(ordered["target"], ratios, color=colors[: len(ordered)])
    ax.set_yscale("log")
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_ylabel("One sigma floor / WHO 2021 guideline")
    ax.set_title("Reference link detection floors at 45 degree elevation")
    ax.grid(True, axis="y", which="both", alpha=0.25)
    for bar, ratio in zip(bars, ratios, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            ratio * 1.15,
            f"{ratio:.0f}x",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.tight_layout()
    fig.savefig(figure_dir / "physical_detection_floor_vs_guideline.png", dpi=220)
    plt.close(fig)

    elevation = sensitivity.loc[
        sensitivity["sensitivity_variable"] == "elevation_deg"
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for index, target in enumerate(REPORT_TARGETS):
        subset = elevation.loc[elevation["target"] == target].sort_values(
            "sensitivity_value"
        )
        ax.semilogy(
            subset["sensitivity_value"],
            subset["floor_to_guideline_ratio"],
            marker="o",
            label=target,
            color=colors[index],
        )
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("Satellite elevation (degrees)")
    ax.set_ylabel("One sigma floor / WHO 2021 guideline")
    ax.set_title("Physical detectability sensitivity to elevation")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(figure_dir / "physical_sensitivity.png", dpi=220)
    plt.close(fig)

    if estimator_metrics is not None:
        selected_models = [
            "training period mean",
            "Ridge selected on validation",
            "oracle gas WLS with true PM removed",
        ]
        subset = estimator_metrics.loc[estimator_metrics["model"].isin(selected_models)]
        pivot = subset.pivot(index="target", columns="model", values="normalized_rmse")
        pivot = pivot.reindex(REPORT_TARGETS)
        fig, ax = plt.subplots(figsize=(7.2, 4.0))
        pivot.plot(kind="bar", logy=True, ax=ax, width=0.8)
        ax.set_xlabel("")
        ax.set_ylabel("Test normalized RMSE")
        ax.set_title("Held out estimation from simulated physical attenuation")
        ax.grid(True, axis="y", which="both", alpha=0.25)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(figure_dir / "physical_estimator_benchmark.png", dpi=220)
        plt.close(fig)


def main() -> None:
    """Execute the complete study and write auditable artifacts."""
    args = parse_args()
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    for path in (args.air_quality, args.hitran_lines):
        if not path.exists():
            raise FileNotFoundError(f"Required input does not exist: {path}")

    print("Loading complete case UCI records and processed HITRAN lines.")
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    hitran = pd.read_csv(args.hitran_lines)
    surface_temperature_k = float(data["temperature_c"].median() + 273.15)
    surface_pressure_pa = float(data["pressure_hpa"].median() * 100.0)
    surface_dew_point_c = float(data["dew_point_c"].median())
    valid_pm = data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]]
    fine_fraction = float(
        np.median(valid_pm["PM2_5_ug_m3"] / valid_pm["PM10_ug_m3"])
    )

    frequency_ghz = np.linspace(60.0, 400.0, BASE_N_FREQUENCIES)
    print("Building the 24 layer Voigt and Rayleigh attenuation design.")
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

    signature_summary, informative = build_signature_summary(data, design, fine_fraction)
    signature_summary.to_csv(table_dir / "physical_signature_summary.csv", index=False)
    informative.to_csv(table_dir / "physical_informative_frequencies.csv", index=False)

    print("Computing Fisher bounds and scenario sensitivity.")
    floor_rows, link_diagnostics = compute_floor_rows(
        design,
        baseline_link_config(BASE_N_FREQUENCIES),
        fine_fraction,
        elevation_deg=BASE_ELEVATION_DEG,
        n_pilots=BASE_N_PILOTS,
        residual_error_std_db=BASE_RESIDUAL_ERROR_STD_DB,
    )
    floors = pd.DataFrame(floor_rows)
    floors.to_csv(table_dir / "physical_detection_floors.csv", index=False)
    sensitivity = run_sensitivity(design, fine_fraction)
    sensitivity.to_csv(table_dir / "physical_sensitivity.csv", index=False)

    scaled_joint = np.column_stack(
        [
            design.gas_db_per_ug_m3
            * np.array(
                [data[AIR_COLUMNS[target]].quantile(0.95) for target in GAS_TARGETS]
            )[None, :],
            design.pm_db_per_ug_m3[:, 0]
            * float(data[AIR_COLUMNS["PM2.5"]].quantile(0.95)),
            design.pm_db_per_ug_m3[:, 1]
            * float(
                (valid_pm["PM10_ug_m3"] - valid_pm["PM2_5_ug_m3"]).quantile(0.95)
            ),
        ]
    )
    singular_values = np.linalg.svd(scaled_joint, compute_uv=False)
    pm_correlation = float(
        np.corrcoef(design.pm_db_per_ug_m3[:, 0], design.pm_db_per_ug_m3[:, 1])[0, 1]
    )

    estimator_metrics = None
    alpha_table = None
    estimator_metadata: dict[str, object] = {"skipped": True}
    if not args.skip_estimators:
        print("Running the chronological held out simulated observation benchmark.")
        estimator_metrics, alpha_table, estimator_metadata = run_estimator_benchmark(
            data,
            design,
            hitran,
            surface_temperature_k,
            surface_pressure_pa,
            surface_dew_point_c,
            args.sample_size,
        )
        estimator_metrics.to_csv(
            table_dir / "physical_estimator_metrics.csv", index=False
        )
        alpha_table.to_csv(table_dir / "physical_ridge_validation.csv", index=False)

    save_figures(
        figure_dir,
        data,
        design,
        fine_fraction,
        floors,
        sensitivity,
        estimator_metrics,
    )

    dependency_versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "hitran-api"):
        try:
            dependency_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependency_versions[package] = "not installed"
    manifest = {
        "study_status": "physical feasibility study with simulated attenuation observations",
        "inputs": {
            "air_quality_path": str(args.air_quality.resolve()),
            "air_quality_sha256": sha256_file(args.air_quality),
            "hitran_path": str(args.hitran_lines.resolve()),
            "hitran_sha256": sha256_file(args.hitran_lines),
            "uci_rows": len(data),
            "hitran_lines": len(hitran),
        },
        "surface_conditions_from_uci_medians": {
            "temperature_k": surface_temperature_k,
            "pressure_pa": surface_pressure_pa,
            "dew_point_c": surface_dew_point_c,
        },
        "atmosphere": {
            "n_layers": 24,
            "top_altitude_m": 12_000.0,
            "pollutant_scale_height_m": 1_500.0,
            "water_scale_height_m": 2_000.0,
            "pm_scale_height_m": 1_000.0,
            "partition_sum_version": 2025,
            "frequency_min_ghz": 60.0,
            "frequency_max_ghz": 400.0,
            "frequency_count": BASE_N_FREQUENCIES,
        },
        "reference_link": asdict(baseline_link_config(BASE_N_FREQUENCIES)),
        "observation": {
            "elevation_deg": BASE_ELEVATION_DEG,
            "n_pilots": BASE_N_PILOTS,
            "residual_error_std_db": BASE_RESIDUAL_ERROR_STD_DB,
            "residual_error_assumption": "independent between tones; borrowed scenario value, not calibrated for this link",
            "variance_model": "(10/ln(10))^2 / Np * (1 + 1/SNR)^2 + sigma_residual^2",
        },
        "sensitivity_design": {
            "primary_sweeps": "one factor at a time around the reference link",
            "optimistic_combined_scenario": {
                "elevation_deg": 15.0,
                "n_pilots": 3_000,
                "residual_error_std_db": 0.0,
                "tx_power_dbm": 33.0,
                "tone_count": BASE_N_FREQUENCIES,
                "interpretation": "optimistic stress test, not a proposed deployment",
            },
        },
        "pm_model": {
            "status": "exploratory Rayleigh model with assumed particle properties",
            "uci_median_fine_fraction_of_pm10": fine_fraction,
            "fine_coarse_signature_correlation": pm_correlation,
            "q95_scaled_design_smallest_to_largest_singular_ratio": float(
                singular_values[-1] / singular_values[0]
            ),
            "joint_pm_interpretation": "practically nonidentifiable",
        },
        "who_comparison": {
            "status": "health guideline comparison, not legal compliance verification",
            "guidelines_ug_m3": WHO_GUIDELINES_UG_M3,
            "averaging_periods": WHO_AVERAGING_PERIOD,
        },
        "link_diagnostics": link_diagnostics,
        "estimator_benchmark": estimator_metadata,
        "dependency_versions": dependency_versions,
        "known_limitations": [
            "No measured sub THz CSI is used.",
            "Pollutant vertical profiles are exponential scale height assumptions.",
            "The frequency samples are multiband probes, not one contiguous OFDM allocation.",
            "PM refractive index, density, and modal diameter are exploratory assumptions.",
            "The UCI station measurements are surface point observations, not column retrieval truth.",
        ],
    }
    with (table_dir / "physical_feasibility_config.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Wrote physical feasibility tables to {table_dir}")
    print(f"Wrote physical feasibility figures to {figure_dir}")
    print(floors[["target", "detection_floor_1sigma_ug_m3", "floor_to_guideline_ratio"]].to_string(index=False))


if __name__ == "__main__":
    main()
