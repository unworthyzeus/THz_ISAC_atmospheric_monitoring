"""Reproduce and stress test the physical estimator normalized RMSE."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from thz_isac.estimation_bounds import (  # noqa: E402
    linear_attenuation_crb,
    pilot_averaged_attenuation_variance_from_snr_db,
)
from thz_isac.evaluation_protocol import (  # noqa: E402
    SplitIndices,
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.linear_gaussian import (  # noqa: E402
    MultiTargetRegressionMetrics,
    coherent_csi_attenuation_variance_db2,
    linear_gaussian_posterior_mean,
    multi_target_regression_metrics,
    orthonormal_column_basis,
    paired_bootstrap_macro_nrmse_difference,
    select_largest_positive_scale_below_target,
    training_quantile_range,
)
from thz_isac.link_budget import (  # noqa: E402
    LEOLinkBudgetConfig,
    compute_leo_link_budget,
)
from thz_isac.physical_spectroscopy import (  # noqa: E402
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
RIDGE_ALPHAS = np.array(
    [0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0,
     1_000_000.0, 10_000_000.0, 100_000_000.0],
    dtype=float,
)
BOOTSTRAP_SEED = 4_401
DEFAULT_TARGET_NRMSE = 0.0347443444


@dataclass(frozen=True)
class BenchmarkContext:
    """Arrays and metadata shared by the audit calculations."""

    data: pd.DataFrame
    eligible: pd.DataFrame
    sample: pd.DataFrame
    sample_indices: np.ndarray
    targets: np.ndarray
    parameter_targets: np.ndarray
    report_design: np.ndarray
    gas_design: np.ndarray
    pm_design: np.ndarray
    background_db: np.ndarray
    noise_variance: np.ndarray
    standardized_noise: np.ndarray
    excess_attenuation: np.ndarray
    observations: np.ndarray
    split: SplitIndices
    denominators: np.ndarray
    snr_db: np.ndarray


@dataclass(frozen=True)
class RidgeAudit:
    """Ridge predictions and validation diagnostics."""

    shared_prediction: np.ndarray
    shared_alpha: float
    target_specific_prediction: np.ndarray
    target_specific_alphas: np.ndarray
    validation_normalized_rmse: np.ndarray
    test_predictions_by_alpha: np.ndarray


def parse_args() -> argparse.Namespace:
    """Parse audit options."""
    parser = argparse.ArgumentParser(
        description="Reproduce and stress test the physical estimator RMSE."
    )
    parser.add_argument(
        "--physical-config",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables" / "physical_feasibility_config.json",
    )
    parser.add_argument(
        "--reported-metrics",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables" / "physical_estimator_metrics.csv",
    )
    parser.add_argument(
        "--reported-ridge-validation",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables" / "physical_ridge_validation.csv",
    )
    parser.add_argument("--air-quality", type=Path, default=None)
    parser.add_argument("--hitran-lines", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables",
    )
    parser.add_argument("--bootstrap-replicates", type=int, default=2_000)
    parser.add_argument("--sampler-replicates", type=int, default=20)
    parser.add_argument("--target-nrmse", type=float, default=DEFAULT_TARGET_NRMSE)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA256 digest for one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_input_path(argument: Path | None, configured: str) -> Path:
    """Resolve an explicit or configured input path."""
    path = argument if argument is not None else Path(configured)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def build_context(
    data: pd.DataFrame,
    hitran: pd.DataFrame,
    config: dict[str, object],
) -> BenchmarkContext:
    """Rebuild the exact physical benchmark observations in memory."""
    estimator_config = config["estimator_benchmark"]
    atmosphere_config = config["atmosphere"]
    observation_config = config["observation"]
    surface_config = config["surface_conditions_from_uci_medians"]
    sample_size = int(estimator_config["simulated_observation_rows"])

    eligible = data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]].copy()
    eligible = eligible.sort_values(["datetime", "station"]).reset_index(drop=True)
    sample_indices = np.linspace(0, len(eligible) - 1, sample_size, dtype=int)
    sample = eligible.iloc[sample_indices].reset_index(drop=True)

    targets = sample[[AIR_COLUMNS[target] for target in REPORT_TARGETS]].to_numpy(float)
    parameter_targets = np.column_stack(
        [targets[:, :5], targets[:, 5] - targets[:, 4]]
    )
    split = chronological_timestamp_split(sample[["datetime", "station"]])
    validate_disjoint_split(split, len(sample))
    denominators = training_quantile_range(targets[split.train])

    frequency_ghz = np.linspace(
        float(atmosphere_config["frequency_min_ghz"]),
        float(atmosphere_config["frequency_max_ghz"]),
        int(atmosphere_config["frequency_count"]),
    )
    design = build_layered_zenith_attenuation_design(
        hitran,
        frequency_ghz,
        surface_dew_point_c=float(surface_config["dew_point_c"]),
        pollutant_scale_height_m=float(atmosphere_config["pollutant_scale_height_m"]),
        water_scale_height_m=float(atmosphere_config["water_scale_height_m"]),
        pm_scale_height_m=float(atmosphere_config["pm_scale_height_m"]),
        n_layers=int(atmosphere_config["n_layers"]),
        top_altitude_m=float(atmosphere_config["top_altitude_m"]),
        surface_temperature_k=float(surface_config["temperature_k"]),
        surface_pressure_pa=float(surface_config["pressure_pa"]),
        partition_sum_version=int(atmosphere_config["partition_sum_version"]),
    )
    elevation_deg = float(observation_config["elevation_deg"])
    gas_design = apply_plane_parallel_slant(design.gas_db_per_ug_m3, elevation_deg)
    pm_design = apply_plane_parallel_slant(design.pm_db_per_ug_m3, elevation_deg)
    parameter_design = np.column_stack([gas_design, pm_design])
    report_design = np.column_stack(
        [gas_design, pm_design[:, 0] - pm_design[:, 1], pm_design[:, 1]]
    )
    background = apply_plane_parallel_slant(design.background_db, elevation_deg)
    link = compute_leo_link_budget(
        frequency_ghz,
        elevation_deg,
        LEOLinkBudgetConfig(**config["reference_link"]),
        atmospheric_loss_db=background,
    )
    snr_db = np.clip(link.snr_db[0], -150.0, 150.0)
    variance = pilot_averaged_attenuation_variance_from_snr_db(
        snr_db,
        int(observation_config["n_pilots"]),
        float(observation_config["residual_error_std_db"]),
    )
    standardized_noise = np.random.default_rng(
        int(estimator_config["random_seed"])
    ).normal(size=(len(sample), len(frequency_ghz)))
    excess = parameter_targets @ parameter_design.T
    observations = excess + standardized_noise * np.sqrt(variance)
    return BenchmarkContext(
        data=data,
        eligible=eligible,
        sample=sample,
        sample_indices=sample_indices,
        targets=targets,
        parameter_targets=parameter_targets,
        report_design=report_design,
        gas_design=gas_design,
        pm_design=pm_design,
        background_db=background,
        noise_variance=variance,
        standardized_noise=standardized_noise,
        excess_attenuation=excess,
        observations=observations,
        split=split,
        denominators=denominators,
        snr_db=snr_db,
    )


def audit_ridge(context: BenchmarkContext) -> RidgeAudit:
    """Reproduce shared alpha Ridge and select target specific alphas."""
    scaler = StandardScaler()
    train_x = scaler.fit_transform(context.observations[context.split.train])
    validation_x = scaler.transform(context.observations[context.split.validation])
    test_x = scaler.transform(context.observations[context.split.test])
    validation_predictions = []
    test_predictions = []
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=float(alpha))
        model.fit(train_x, context.targets[context.split.train])
        validation_predictions.append(model.predict(validation_x))
        test_predictions.append(model.predict(test_x))
    validation_stack = np.asarray(validation_predictions)
    test_stack = np.asarray(test_predictions)
    validation_rmse = np.sqrt(
        np.mean(
            (validation_stack - context.targets[context.split.validation][None, :, :]) ** 2,
            axis=1,
        )
    )
    validation_nrmse = validation_rmse / context.denominators[None, :]
    shared_index = int(np.argmin(np.mean(validation_nrmse, axis=1)))
    target_indices = np.argmin(validation_nrmse, axis=0)
    target_prediction = np.column_stack(
        [test_stack[target_indices[index], :, index] for index in range(len(REPORT_TARGETS))]
    )
    return RidgeAudit(
        shared_prediction=test_stack[shared_index],
        shared_alpha=float(RIDGE_ALPHAS[shared_index]),
        target_specific_prediction=target_prediction,
        target_specific_alphas=RIDGE_ALPHAS[target_indices],
        validation_normalized_rmse=validation_nrmse,
        test_predictions_by_alpha=test_stack,
    )


def refit_ridge_on_development(
    context: BenchmarkContext,
    alpha: float,
) -> np.ndarray:
    """Refit the selected Ridge pipeline on training plus validation rows."""
    development = np.concatenate([context.split.train, context.split.validation])
    scaler = StandardScaler()
    development_x = scaler.fit_transform(context.observations[development])
    test_x = scaler.transform(context.observations[context.split.test])
    model = Ridge(alpha=alpha)
    model.fit(development_x, context.targets[development])
    return model.predict(test_x)


def metric_for_prediction(
    context: BenchmarkContext,
    prediction: np.ndarray,
    indices: np.ndarray | None = None,
) -> MultiTargetRegressionMetrics:
    """Evaluate a prediction on test rows unless other indices are supplied."""
    selected = context.split.test if indices is None else np.asarray(indices, dtype=int)
    return multi_target_regression_metrics(
        context.targets[selected],
        prediction,
        context.denominators,
    )


def mean_baseline_for_frame(frame: pd.DataFrame) -> dict[str, object]:
    """Return the chronological training mean metric for one sampled frame."""
    ordered = frame.sort_values(["datetime", "station"]).reset_index(drop=True)
    split = chronological_timestamp_split(ordered[["datetime", "station"]])
    validate_disjoint_split(split, len(ordered))
    targets = ordered[[AIR_COLUMNS[target] for target in REPORT_TARGETS]].to_numpy(float)
    denominators = training_quantile_range(targets[split.train])
    train_mean = np.mean(targets[split.train], axis=0)
    prediction = np.broadcast_to(train_mean, targets[split.test].shape)
    metrics = multi_target_regression_metrics(
        targets[split.test],
        prediction,
        denominators,
    )
    return {
        "row_count": len(ordered),
        "unique_timestamps": int(ordered["datetime"].nunique()),
        "train_rows": len(split.train),
        "validation_rows": len(split.validation),
        "test_rows": len(split.test),
        "train_end": str(split.train_end),
        "validation_end": str(split.validation_end),
        "macro_normalized_rmse": metrics.macro_normalized_rmse,
    }


def sampler_sensitivity(
    context: BenchmarkContext,
    n_random_samples: int,
) -> list[dict[str, object]]:
    """Compare the mean baseline under deterministic and random row samples."""
    if n_random_samples < 1:
        raise ValueError("sampler_replicates must be a positive integer")
    rows: list[dict[str, object]] = []

    current = mean_baseline_for_frame(context.sample)
    current.update({"case": "deterministic_linspace", "seed": -1})
    rows.append(current)

    full = mean_baseline_for_frame(context.eligible)
    full.update({"case": "all_eligible_rows", "seed": -1})
    rows.append(full)

    unique_times = np.sort(context.eligible["datetime"].unique())
    selected_times = unique_times[
        np.linspace(0, len(unique_times) - 1, len(context.sample), dtype=int)
    ]
    even_timestamp = context.eligible.loc[
        context.eligible["datetime"].isin(selected_times)
    ].drop_duplicates("datetime", keep="first")
    even = mean_baseline_for_frame(even_timestamp)
    even.update({"case": "even_timestamps_first_station", "seed": -1})
    rows.append(even)

    for seed in range(n_random_samples):
        indices = np.random.default_rng(seed).choice(
            len(context.eligible),
            len(context.sample),
            replace=False,
        )
        random_result = mean_baseline_for_frame(context.eligible.iloc[indices])
        random_result.update({"case": "random_rows", "seed": seed})
        rows.append(random_result)
    return rows


def add_metric_details(
    rows: list[dict[str, object]],
    case: str,
    metrics: MultiTargetRegressionMetrics,
    notes: str = "",
) -> None:
    """Append tidy per target metrics."""
    metric_arrays = {
        "mae": (metrics.mae, "ug/m3"),
        "rmse": (metrics.rmse, "ug/m3"),
        "normalized_rmse": (metrics.normalized_rmse, "dimensionless"),
        "r2": (metrics.r2, "dimensionless"),
        "bias": (metrics.bias, "ug/m3"),
    }
    for target_index, target in enumerate(REPORT_TARGETS):
        for metric, (values, unit) in metric_arrays.items():
            add_detail(
                rows,
                "model_metrics",
                case,
                target,
                metric,
                float(values[target_index]),
                unit,
                notes,
            )


def add_detail(
    rows: list[dict[str, object]],
    section: str,
    case: str,
    target: str,
    metric: str,
    value: float,
    unit: str,
    notes: str = "",
) -> None:
    """Append one tidy audit result."""
    rows.append(
        {
            "section": section,
            "case": case,
            "target": target,
            "metric": metric,
            "value": float(value),
            "unit": unit,
            "notes": notes,
        }
    )


def add_summary(
    rows: list[dict[str, object]],
    result: str,
    value: float,
    unit: str,
    status: str,
    notes: str,
) -> None:
    """Append one headline audit result."""
    rows.append(
        {
            "result": result,
            "value": float(value),
            "unit": unit,
            "status": status,
            "notes": notes,
        }
    )


def main() -> None:
    """Run the complete reproducible RMSE audit."""
    args = parse_args()
    for path in (
        args.physical_config,
        args.reported_metrics,
        args.reported_ridge_validation,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Required audit input does not exist: {path}")
    with args.physical_config.open("r", encoding="utf-8") as handle:
        physical_config = json.load(handle)
    air_quality_path = resolve_input_path(
        args.air_quality,
        physical_config["inputs"]["air_quality_path"],
    )
    hitran_path = resolve_input_path(
        args.hitran_lines,
        physical_config["inputs"]["hitran_path"],
    )
    for path in (air_quality_path, hitran_path):
        if not path.exists():
            raise FileNotFoundError(f"Required source input does not exist: {path}")
    if sha256_file(air_quality_path) != physical_config["inputs"]["air_quality_sha256"]:
        raise ValueError("Air quality input hash differs from the physical benchmark manifest")
    if sha256_file(hitran_path) != physical_config["inputs"]["hitran_sha256"]:
        raise ValueError("HITRAN input hash differs from the physical benchmark manifest")
    if args.bootstrap_replicates < 1 or args.sampler_replicates < 1:
        raise ValueError("replicate counts must be positive")
    if not np.isfinite(args.target_nrmse) or args.target_nrmse <= 0.0:
        raise ValueError("target_nrmse must be strictly positive")

    print("Loading the hashed UCI and HITRAN inputs.")
    data = pd.read_csv(air_quality_path, parse_dates=["datetime"])
    hitran = pd.read_csv(hitran_path)
    print("Rebuilding the exact 20,000 row physical observation benchmark.")
    context = build_context(data, hitran, physical_config)
    ridge = audit_ridge(context)

    truth_test = context.targets[context.split.test]
    train_mean = np.mean(context.targets[context.split.train], axis=0)
    mean_prediction = np.broadcast_to(train_mean, truth_test.shape)
    validation_mean = np.mean(context.targets[context.split.validation], axis=0)
    validation_mean_prediction = np.broadcast_to(validation_mean, truth_test.shape)

    prior_mean = train_mean
    prior_covariance = np.cov(context.targets[context.split.train], rowvar=False, ddof=1)
    lmmse = linear_gaussian_posterior_mean(
        context.observations[context.split.test],
        context.report_design,
        context.noise_variance,
        prior_mean,
        prior_covariance,
    ).prediction
    refit_prediction = refit_ridge_on_development(context, ridge.shared_alpha)

    observation_config = physical_config["observation"]
    snr_linear = 10.0 ** (context.snr_db / 10.0)
    coherent_variance = coherent_csi_attenuation_variance_db2(
        snr_linear,
        int(observation_config["n_pilots"]),
        float(observation_config["residual_error_std_db"]),
    )
    coherent_zero_residual_variance = coherent_csi_attenuation_variance_db2(
        snr_linear,
        int(observation_config["n_pilots"]),
        0.0,
    )
    coherent_observations = (
        context.excess_attenuation
        + context.standardized_noise * np.sqrt(coherent_variance)
    )
    coherent_zero_observations = (
        context.excess_attenuation
        + context.standardized_noise * np.sqrt(coherent_zero_residual_variance)
    )
    coherent_prediction = linear_gaussian_posterior_mean(
        coherent_observations[context.split.test],
        context.report_design,
        coherent_variance,
        prior_mean,
        prior_covariance,
    ).prediction
    coherent_zero_prediction = linear_gaussian_posterior_mean(
        coherent_zero_observations[context.split.test],
        context.report_design,
        coherent_zero_residual_variance,
        prior_mean,
        prior_covariance,
    ).prediction

    model_predictions = {
        "training_period_mean": mean_prediction,
        "ridge_shared_validation_alpha": ridge.shared_prediction,
        "ridge_target_specific_validation_alpha": ridge.target_specific_prediction,
        "physics_lmmse_pilot_power": lmmse,
        "ridge_refit_train_validation": refit_prediction,
        "validation_period_mean_no_thz": validation_mean_prediction,
        "physics_lmmse_coherent_csi_residual": coherent_prediction,
        "physics_lmmse_coherent_csi_zero_residual": coherent_zero_prediction,
    }
    model_metrics = {
        case: multi_target_regression_metrics(
            truth_test,
            prediction,
            context.denominators,
        )
        for case, prediction in model_predictions.items()
    }

    reported_metrics = pd.read_csv(args.reported_metrics)
    reported_ridge = reported_metrics.loc[
        (reported_metrics["model"] == "Ridge selected on validation")
        & (reported_metrics["split"] == "test")
    ]
    reported_mean = reported_metrics.loc[
        (reported_metrics["model"] == "training period mean")
        & (reported_metrics["split"] == "test")
    ]
    if len(reported_ridge) != len(REPORT_TARGETS) or len(reported_mean) != len(REPORT_TARGETS):
        raise ValueError("Reported metric table does not contain all six expected targets")
    reported_headline = float(reported_ridge["normalized_rmse"].mean())
    reported_mean_headline = float(reported_mean["normalized_rmse"].mean())
    reproduced_headline = model_metrics[
        "ridge_shared_validation_alpha"
    ].macro_normalized_rmse
    reproduction_difference = reproduced_headline - reported_headline
    if abs(reproduction_difference) > 1.0e-12:
        raise AssertionError(
            "Reproduced Ridge headline differs from the reported artifact by more than 1e-12"
        )

    reported_validation = pd.read_csv(args.reported_ridge_validation)
    reproduced_validation_macro = np.mean(ridge.validation_normalized_rmse, axis=1)
    if not np.allclose(
        reported_validation["validation_mean_normalized_rmse"],
        reproduced_validation_macro,
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise AssertionError("Reproduced Ridge validation sweep differs from its artifact")

    print("Running the paired bootstrap and sampler sensitivity audit.")
    bootstrap = paired_bootstrap_macro_nrmse_difference(
        truth_test,
        ridge.shared_prediction,
        mean_prediction,
        context.denominators,
        n_resamples=args.bootstrap_replicates,
        random_seed=BOOTSTRAP_SEED,
    )
    sampler_rows = sampler_sensitivity(context, args.sampler_replicates)
    random_sampler_values = np.array(
        [
            row["macro_normalized_rmse"]
            for row in sampler_rows
            if row["case"] == "random_rows"
        ],
        dtype=float,
    )

    nuisance = orthonormal_column_basis(
        np.column_stack(
            [
                np.ones_like(context.background_db),
                context.background_db,
                context.pm_design[:, 0],
                context.pm_design[:, 1],
            ]
        )
    )
    variance_cases = {
        "pilot_power_residual": context.noise_variance,
        "coherent_csi_residual": coherent_variance,
        "coherent_csi_zero_residual": coherent_zero_residual_variance,
    }
    gas_crb = {
        case: linear_attenuation_crb(
            context.gas_design,
            variance,
            nuisance_design=nuisance,
            rcond=1.0e-12,
        )
        for case, variance in variance_cases.items()
    }

    signal_std = np.std(
        context.excess_attenuation[context.split.train],
        axis=0,
        ddof=1,
    )
    signal_noise_ratio = signal_std / np.sqrt(context.noise_variance)
    fisher = context.report_design.T @ (
        context.report_design / context.noise_variance[:, None]
    )
    prior_cholesky = np.linalg.cholesky(prior_covariance)
    prior_whitened_eigenvalues = np.linalg.eigvalsh(
        prior_cholesky.T @ fisher @ prior_cholesky
    )

    def noise_scaled_metrics(
        scale: float,
        indices: np.ndarray,
    ) -> MultiTargetRegressionMetrics:
        variance = context.noise_variance * scale**2
        observations = (
            context.excess_attenuation[indices]
            + context.standardized_noise[indices] * np.sqrt(variance)
        )
        prediction = linear_gaussian_posterior_mean(
            observations,
            context.report_design,
            variance,
            prior_mean,
            prior_covariance,
        ).prediction
        return multi_target_regression_metrics(
            context.targets[indices],
            prediction,
            context.denominators,
        )

    print("Selecting the idealized global noise scale on validation only.")
    noise_selection = select_largest_positive_scale_below_target(
        lambda scale: noise_scaled_metrics(
            scale,
            context.split.validation,
        ).macro_normalized_rmse,
        float(args.target_nrmse),
        1.0e-7,
        1.0e-3,
        iterations=60,
    )
    selected_validation_metrics = noise_scaled_metrics(
        noise_selection.selected_scale,
        context.split.validation,
    )
    selected_test_metrics = noise_scaled_metrics(
        noise_selection.selected_scale,
        context.split.test,
    )
    noise_std_reduction = 1.0 / noise_selection.selected_scale
    independent_repeat_equivalent = noise_std_reduction**2
    pilot_symbol_equivalent = (
        independent_repeat_equivalent * int(observation_config["n_pilots"])
    )

    detail_rows: list[dict[str, object]] = []
    for case, metrics in model_metrics.items():
        add_metric_details(detail_rows, case, metrics)
    for target, denominator in zip(REPORT_TARGETS, context.denominators, strict=True):
        add_detail(
            detail_rows,
            "metric_definition",
            "training_q05_q95",
            target,
            "normalization_denominator",
            float(denominator),
            "ug/m3",
        )
    for alpha_index, alpha in enumerate(RIDGE_ALPHAS):
        add_detail(
            detail_rows,
            "ridge_validation",
            "shared_alpha_grid",
            "macro",
            f"alpha_{alpha:g}_normalized_rmse",
            float(reproduced_validation_macro[alpha_index]),
            "dimensionless",
        )
        for target_index, target in enumerate(REPORT_TARGETS):
            add_detail(
                detail_rows,
                "ridge_validation",
                "per_target_alpha_grid",
                target,
                f"alpha_{alpha:g}_normalized_rmse",
                float(ridge.validation_normalized_rmse[alpha_index, target_index]),
                "dimensionless",
            )
    for target, alpha in zip(REPORT_TARGETS, ridge.target_specific_alphas, strict=True):
        add_detail(
            detail_rows,
            "ridge_selection",
            "target_specific_validation_alpha",
            target,
            "selected_alpha",
            float(alpha),
            "alpha",
        )
    for replicate, difference in enumerate(bootstrap.differences):
        add_detail(
            detail_rows,
            "paired_bootstrap",
            f"replicate_{replicate:04d}",
            "macro",
            "ridge_minus_mean_normalized_rmse",
            float(difference),
            "dimensionless",
            "Paired row resample of the fixed 4,000 row test predictions.",
        )
    for row in sampler_rows:
        add_detail(
            detail_rows,
            "sampler_sensitivity",
            f"{row['case']}_seed_{row['seed']}",
            "macro",
            "training_mean_normalized_rmse",
            float(row["macro_normalized_rmse"]),
            "dimensionless",
            f"rows={row['row_count']}; unique_timestamps={row['unique_timestamps']}; "
            f"train={row['train_rows']}; validation={row['validation_rows']}; "
            f"test={row['test_rows']}; train_end={row['train_end']}; "
            f"validation_end={row['validation_end']}",
        )
    for case, crb in gas_crb.items():
        for target, floor in zip(GAS_TARGETS, crb.target_standard_deviation, strict=True):
            add_detail(
                detail_rows,
                "pilot_variance_sensitivity",
                case,
                target,
                "nuisance_aware_crb_1sigma",
                float(floor),
                "ug/m3",
            )
    for split_name, metrics in (
        ("validation", selected_validation_metrics),
        ("test", selected_test_metrics),
    ):
        for target, value in zip(REPORT_TARGETS, metrics.normalized_rmse, strict=True):
            add_detail(
                detail_rows,
                "noise_requirement",
                split_name,
                target,
                "normalized_rmse",
                float(value),
                "dimensionless",
                "Global diagonal observation noise standard deviation scaling.",
            )

    summary_rows: list[dict[str, object]] = []
    add_summary(
        summary_rows,
        "reported_ridge_macro_normalized_rmse",
        reported_headline,
        "dimensionless",
        "verified",
        "Mean of the six rows in physical_estimator_metrics.csv.",
    )
    add_summary(
        summary_rows,
        "reproduced_ridge_macro_normalized_rmse",
        reproduced_headline,
        "dimensionless",
        "verified",
        "Rebuilt from the hashed UCI and HITRAN inputs.",
    )
    add_summary(
        summary_rows,
        "ridge_reproduction_absolute_difference",
        abs(reproduction_difference),
        "dimensionless",
        "verified",
        "Required tolerance is 1e-12.",
    )
    for case, metrics in model_metrics.items():
        add_summary(
            summary_rows,
            f"{case}_macro_normalized_rmse",
            metrics.macro_normalized_rmse,
            "dimensionless",
            "diagnostic",
            "All methods use the original fixed chronological test rows.",
        )
        add_summary(
            summary_rows,
            f"{case}_mean_r2",
            metrics.mean_r2,
            "dimensionless",
            "diagnostic",
            "Unweighted mean across six target R2 values.",
        )
    add_summary(
        summary_rows,
        "reported_training_mean_macro_normalized_rmse",
        reported_mean_headline,
        "dimensionless",
        "verified",
        "Controlling baseline from the original metric artifact.",
    )
    add_summary(
        summary_rows,
        "ridge_minus_training_mean_macro_normalized_rmse",
        bootstrap.observed_difference,
        "dimensionless",
        "diagnostic",
        "Negative favors Ridge.",
    )
    add_summary(
        summary_rows,
        "paired_bootstrap_95pct_lower",
        bootstrap.confidence_lower,
        "dimensionless",
        "diagnostic",
        "Percentile interval from paired test row resampling.",
    )
    add_summary(
        summary_rows,
        "paired_bootstrap_95pct_upper",
        bootstrap.confidence_upper,
        "dimensionless",
        "diagnostic",
        "Interval includes zero when the apparent gain is not resolved.",
    )
    add_summary(
        summary_rows,
        "paired_bootstrap_probability_ridge_better",
        bootstrap.probability_candidate_better,
        "probability",
        "diagnostic",
        "Conditional on the fixed split, fit, and simulated noise realization.",
    )
    current_sampler = next(
        row for row in sampler_rows if row["case"] == "deterministic_linspace"
    )
    all_sampler = next(row for row in sampler_rows if row["case"] == "all_eligible_rows")
    add_summary(
        summary_rows,
        "deterministic_sampler_training_mean_macro_normalized_rmse",
        float(current_sampler["macro_normalized_rmse"]),
        "dimensionless",
        "verified",
        "The current sample retains one row per selected timestamp.",
    )
    add_summary(
        summary_rows,
        "all_eligible_rows_training_mean_macro_normalized_rmse",
        float(all_sampler["macro_normalized_rmse"]),
        "dimensionless",
        "diagnostic",
        "Uses every row satisfying PM10 greater than or equal to PM2.5.",
    )
    for name, value in (
        ("random_sampler_macro_normalized_rmse_mean", np.mean(random_sampler_values)),
        ("random_sampler_macro_normalized_rmse_std", np.std(random_sampler_values, ddof=1)),
        ("random_sampler_macro_normalized_rmse_min", np.min(random_sampler_values)),
        ("random_sampler_macro_normalized_rmse_max", np.max(random_sampler_values)),
    ):
        add_summary(
            summary_rows,
            name,
            float(value),
            "dimensionless",
            "diagnostic",
            f"Across {args.sampler_replicates} random 20,000 row samples.",
        )
    add_summary(
        summary_rows,
        "maximum_tone_signal_std_to_noise_std",
        float(np.max(signal_noise_ratio)),
        "ratio",
        "diagnostic",
        "Training excess attenuation standard deviation divided by declared noise.",
    )
    add_summary(
        summary_rows,
        "prior_whitened_fisher_maximum_eigenvalue",
        float(np.max(prior_whitened_eigenvalues)),
        "dimensionless",
        "diagnostic",
        "Values much smaller than one imply little measurement information versus the prior.",
    )
    for name, value, unit, notes in (
        (
            "requested_target_macro_normalized_rmse",
            args.target_nrmse,
            "dimensionless",
            "Tenfold target supplied for the audit.",
        ),
        (
            "validation_selected_global_noise_std_factor",
            noise_selection.selected_scale,
            "factor",
            "Selected using validation labels only after the target was fixed.",
        ),
        (
            "validation_selected_noise_std_reduction",
            noise_std_reduction,
            "factor",
            "Reciprocal of the selected global standard deviation factor.",
        ),
        (
            "ideal_independent_repeat_equivalent",
            independent_repeat_equivalent,
            "repeats",
            "Valid only if every observation error component averages independently.",
        ),
        (
            "ideal_pilot_symbol_equivalent",
            pilot_symbol_equivalent,
            "pilot_symbols",
            "Independent repeat equivalent multiplied by 30 pilots.",
        ),
        (
            "selected_noise_validation_macro_normalized_rmse",
            selected_validation_metrics.macro_normalized_rmse,
            "dimensionless",
            "The selection boundary on validation.",
        ),
        (
            "selected_noise_test_macro_normalized_rmse",
            selected_test_metrics.macro_normalized_rmse,
            "dimensionless",
            "Test evaluated once at the validation selected scale.",
        ),
    ):
        add_summary(summary_rows, name, float(value), unit, "diagnostic", notes)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = output_dir / "rmse_metric_audit_details.csv"
    summary_path = output_dir / "rmse_metric_audit_summary.csv"
    manifest_path = output_dir / "rmse_metric_audit_manifest.json"
    pd.DataFrame(detail_rows).to_csv(detail_path, index=False)
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)

    dependency_versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "hitran-api"):
        try:
            dependency_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependency_versions[package] = "not installed"
    manifest = {
        "audit_status": "reproducible metric and information sensitivity audit",
        "metric_definition": {
            "per_target": "RMSE divided by training Q95 minus training Q05",
            "headline": "unweighted mean across six per target normalized RMSE values",
            "targets": list(REPORT_TARGETS),
            "requested_target_macro_normalized_rmse": float(args.target_nrmse),
        },
        "inputs": {
            "air_quality_path": str(air_quality_path),
            "air_quality_sha256": sha256_file(air_quality_path),
            "hitran_path": str(hitran_path),
            "hitran_sha256": sha256_file(hitran_path),
            "physical_config_path": str(args.physical_config.resolve()),
            "physical_config_sha256": sha256_file(args.physical_config),
            "reported_metrics_path": str(args.reported_metrics.resolve()),
            "reported_metrics_sha256": sha256_file(args.reported_metrics),
            "reported_ridge_validation_path": str(args.reported_ridge_validation.resolve()),
            "reported_ridge_validation_sha256": sha256_file(
                args.reported_ridge_validation
            ),
        },
        "reproduction": {
            "reported_ridge_macro_normalized_rmse": reported_headline,
            "reproduced_ridge_macro_normalized_rmse": reproduced_headline,
            "absolute_difference": abs(reproduction_difference),
            "tolerance": 1.0e-12,
            "passed": bool(abs(reproduction_difference) <= 1.0e-12),
            "shared_alpha": ridge.shared_alpha,
            "target_specific_alphas": {
                target: float(alpha)
                for target, alpha in zip(
                    REPORT_TARGETS,
                    ridge.target_specific_alphas,
                    strict=True,
                )
            },
        },
        "sample_and_split": {
            "eligible_rows": len(context.eligible),
            "excluded_pm_ordering_rows": len(context.data) - len(context.eligible),
            "sample_rows": len(context.sample),
            "unique_sample_indices": int(np.unique(context.sample_indices).size),
            "unique_sample_timestamps": int(context.sample["datetime"].nunique()),
            "minimum_sample_index_gap": int(np.min(np.diff(context.sample_indices))),
            "maximum_sample_index_gap": int(np.max(np.diff(context.sample_indices))),
            "train_rows": len(context.split.train),
            "validation_rows": len(context.split.validation),
            "test_rows": len(context.split.test),
            "train_end": str(context.split.train_end),
            "validation_end": str(context.split.validation_end),
            "sampler_random_replicates": int(args.sampler_replicates),
            "random_sample_macro_normalized_rmse_mean": float(
                np.mean(random_sampler_values)
            ),
            "random_sample_macro_normalized_rmse_std": float(
                np.std(random_sampler_values, ddof=1)
            ),
        },
        "paired_bootstrap": {
            "comparison": "shared alpha Ridge minus training period mean",
            "replicates": int(args.bootstrap_replicates),
            "random_seed": BOOTSTRAP_SEED,
            "confidence_level": bootstrap.confidence_level,
            "observed_difference": bootstrap.observed_difference,
            "confidence_lower": bootstrap.confidence_lower,
            "confidence_upper": bootstrap.confidence_upper,
            "probability_ridge_better": bootstrap.probability_candidate_better,
            "scope": "paired row resampling conditional on fixed split, fit, and noise",
        },
        "information_diagnostics": {
            "tone_signal_std_to_noise_std_max": float(np.max(signal_noise_ratio)),
            "tone_signal_std_to_noise_std_median": float(np.median(signal_noise_ratio)),
            "tone_signal_std_to_noise_std_q95": float(
                np.quantile(signal_noise_ratio, 0.95)
            ),
            "tone_signal_std_to_noise_std_sum_squared": float(
                np.sum(signal_noise_ratio**2)
            ),
            "prior_whitened_fisher_eigenvalues": prior_whitened_eigenvalues.tolist(),
        },
        "pilot_variance_sensitivity": {
            case: {
                "physics_lmmse_macro_normalized_rmse": model_metrics[model_case]
                .macro_normalized_rmse,
                "gas_crb_1sigma_ug_m3": {
                    target: float(value)
                    for target, value in zip(
                        GAS_TARGETS,
                        gas_crb[case].target_standard_deviation,
                        strict=True,
                    )
                },
            }
            for case, model_case in (
                ("pilot_power_residual", "physics_lmmse_pilot_power"),
                ("coherent_csi_residual", "physics_lmmse_coherent_csi_residual"),
                (
                    "coherent_csi_zero_residual",
                    "physics_lmmse_coherent_csi_zero_residual",
                ),
            )
        },
        "validation_selected_noise_requirement": {
            "selection_split": "validation",
            "evaluation_split": "test",
            "lower_scale": 1.0e-7,
            "upper_scale": 1.0e-3,
            "bisection_iterations": noise_selection.iterations,
            "selected_noise_std_factor": noise_selection.selected_scale,
            "noise_std_reduction_factor": noise_std_reduction,
            "ideal_independent_repeat_equivalent": independent_repeat_equivalent,
            "ideal_pilot_symbol_equivalent": pilot_symbol_equivalent,
            "validation_macro_normalized_rmse": (
                selected_validation_metrics.macro_normalized_rmse
            ),
            "test_macro_normalized_rmse": selected_test_metrics.macro_normalized_rmse,
            "test_target_passed": bool(
                selected_test_metrics.macro_normalized_rmse <= args.target_nrmse
            ),
            "caveat": (
                "This scales every diagonal noise standard deviation and assumes exact "
                "forward physics. The repeat equivalent is valid only for independent, "
                "stationary errors and is not a hardware requirement."
            ),
        },
        "dependency_versions": dependency_versions,
        "source_files": {
            "audit_script": str(Path(__file__).resolve()),
            "audit_script_sha256": sha256_file(Path(__file__).resolve()),
            "linear_gaussian_module": str(
                (PROJECT_ROOT / "src" / "thz_isac" / "linear_gaussian.py").resolve()
            ),
            "linear_gaussian_module_sha256": sha256_file(
                PROJECT_ROOT / "src" / "thz_isac" / "linear_gaussian.py"
            ),
        },
        "artifacts": {
            "details_csv": str(detail_path),
            "details_csv_sha256": sha256_file(detail_path),
            "summary_csv": str(summary_path),
            "summary_csv_sha256": sha256_file(summary_path),
        },
        "limitations": [
            "All attenuation observations remain simulated.",
            "The row bootstrap does not preserve temporal or station dependence.",
            "Sampler sensitivity uses the training mean baseline rather than refitting Ridge.",
            "The coherent CSI variance is a high SNR delta method sensitivity case.",
            "The global noise requirement is an idealized information sensitivity test.",
            "The target was chosen after the original test headline was already known.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)

    print(f"Reported Ridge macro normalized RMSE: {reported_headline:.15f}")
    print(f"Reproduced Ridge macro normalized RMSE: {reproduced_headline:.15f}")
    print(
        "Paired bootstrap 95 percent interval for Ridge minus mean: "
        f"[{bootstrap.confidence_lower:.9g}, {bootstrap.confidence_upper:.9g}]"
    )
    print(
        "Validation selected global noise standard deviation reduction: "
        f"{noise_std_reduction:.6g} times"
    )
    print(
        "Test macro normalized RMSE at the selected factor: "
        f"{selected_test_metrics.macro_normalized_rmse:.12f}"
    )
    print(f"Wrote {detail_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
