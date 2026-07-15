"""Run a fixed ten seed stability study for spectral only estimators.

Real UCI Beijing pollutant labels and processed HITRAN line parameters are
used to generate the same modeled attenuation signal as the physical
feasibility benchmark. The sub THz observations remain simulated.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import MultiTaskElasticNet, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.estimation_bounds import (  # noqa: E402
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
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
)
from thz_isac.spectral_model_stability import (  # noqa: E402
    compose_per_target_predictions,
    regression_metric_arrays,
    select_models_per_target,
    summarize_stability_metrics,
)


REPORT_TARGETS = ("CO", "O3", "SO2", "NO2", "PM2.5", "PM10")
AIR_COLUMNS = {
    "CO": "CO_ug_m3",
    "O3": "O3_ug_m3",
    "SO2": "SO2_ug_m3",
    "NO2": "NO2_ug_m3",
    "PM2.5": "PM2_5_ug_m3",
    "PM10": "PM10_ug_m3",
}
PRIMARY_NOISE_SEED = 20260715
NOISE_SEEDS = tuple(range(PRIMARY_NOISE_SEED, PRIMARY_NOISE_SEED + 10))
SAMPLE_SIZE = 20_000
N_FREQUENCIES = 256
ELEVATION_DEG = 45.0
N_PILOTS = 30
RESIDUAL_ERROR_STD_DB = 0.63
RIDGE_ALPHAS = (
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
)
EXPLORATORY_TARGET_RIDGE_ALPHAS = tuple(np.logspace(-2, 12, 29))
ELASTIC_NET_CONFIG = {
    "alpha": 0.01,
    "l1_ratio": 0.8,
    "fit_intercept": True,
    "max_iter": 5_000,
    "tol": 1e-5,
    "random_state": PRIMARY_NOISE_SEED,
    "selection": "cyclic",
}
HISTOGRAM_BOOSTING_CONFIG = {
    "learning_rate": 0.05,
    "max_iter": 100,
    "max_leaf_nodes": 7,
    "min_samples_leaf": 100,
    "l2_regularization": 10.0,
    "early_stopping": True,
    "validation_fraction": 0.1,
    "n_iter_no_change": 10,
}
PCA_KNN_CONFIG = {
    "pca_components": 32,
    "pca_solver": "randomized",
    "n_neighbors": 200,
    "weights": "uniform",
    "p": 2,
}
COMPOSITE_CANDIDATE_ORDER = (
    "histogram_gradient_boosting_frozen",
    "exploratory_pca_knn_component",
    "exploratory_targetwise_ridge_component",
    "multitask_elastic_net_frozen",
)
REFERENCE_MODEL = "ridge_validation_selected"
EXPECTED_AIR_SHA256 = "39d6ceee9d66824bccf68553293a490199084299174496db51fac42bcbc543f0"
EXPECTED_HITRAN_SHA256 = "7d063e4036da3d3e5b75128ff954bc9d80159e63d1831c4bbf75a99bfdaeded8"
EXPECTED_PRIMARY_RIDGE_TEST_NRMSE = 0.34744344415084005


def parse_args() -> argparse.Namespace:
    """Parse input and output path overrides without changing the frozen study."""
    parser = argparse.ArgumentParser(
        description="Run the fixed ten seed spectral estimator stability study."
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
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def baseline_link_config() -> LEOLinkBudgetConfig:
    """Return the exact reference link used by the physical benchmark."""
    return LEOLinkBudgetConfig(
        satellite_altitude_km=550.0,
        tx_power_dbm=23.0,
        tx_aperture_diameter_m=0.5,
        rx_aperture_diameter_m=0.3,
        subcarrier_bandwidth_hz=1_000_000.0,
        tx_aperture_efficiency=0.65,
        rx_aperture_efficiency=0.65,
        receiver_noise_figure_db=6.0,
        receiver_noise_temperature_k=290.0,
        implementation_loss_db=5.0,
        earth_radius_km=6_371.0,
        n_active_subcarriers=N_FREQUENCIES,
    )


def safe_observation_variance(snr_db: np.ndarray) -> np.ndarray:
    """Evaluate the reference pilot variance with opaque tones clipped safely."""
    clipped_snr = np.clip(np.asarray(snr_db, dtype=float), -150.0, 150.0)
    return pilot_averaged_attenuation_variance_from_snr_db(
        clipped_snr,
        N_PILOTS,
        RESIDUAL_ERROR_STD_DB,
    )


def prepare_study_arrays(
    data: pd.DataFrame,
    hitran: pd.DataFrame,
) -> dict[str, object]:
    """Build the frozen signal matrix, real targets, and chronological split."""
    surface_temperature_k = float(data["temperature_c"].median() + 273.15)
    surface_pressure_pa = float(data["pressure_hpa"].median() * 100.0)
    surface_dew_point_c = float(data["dew_point_c"].median())
    frequency_ghz = np.linspace(60.0, 400.0, N_FREQUENCIES)
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

    physically_ordered = data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]].copy()
    physically_ordered = physically_ordered.sort_values(["datetime", "station"]).reset_index(drop=True)
    sample_indices = np.linspace(0, len(physically_ordered) - 1, SAMPLE_SIZE, dtype=int)
    sample = physically_ordered.iloc[sample_indices].reset_index(drop=True)
    targets = sample[[AIR_COLUMNS[target] for target in REPORT_TARGETS]].to_numpy(float)
    parameters = np.column_stack(
        [
            targets[:, :5],
            targets[:, 5] - targets[:, 4],
        ]
    )
    split = chronological_timestamp_split(sample[["datetime", "station"]])
    validate_disjoint_split(split, len(sample))

    gas_design = apply_plane_parallel_slant(design.gas_db_per_ug_m3, ELEVATION_DEG)
    pm_design = apply_plane_parallel_slant(design.pm_db_per_ug_m3, ELEVATION_DEG)
    joint_design = np.column_stack([gas_design, pm_design])
    background = apply_plane_parallel_slant(design.background_db, ELEVATION_DEG)
    link = compute_leo_link_budget(
        design.frequency_ghz,
        ELEVATION_DEG,
        baseline_link_config(),
        atmospheric_loss_db=background,
    )
    variance = safe_observation_variance(link.snr_db[0])
    signal = parameters @ joint_design.T
    denominators = np.quantile(targets[split.train], 0.95, axis=0) - np.quantile(
        targets[split.train], 0.05, axis=0
    )
    if np.any(denominators <= 0.0):
        raise ValueError("Training target normalization ranges must be positive")

    return {
        "sample": sample,
        "targets": targets,
        "signal": signal,
        "variance": variance,
        "denominators": denominators,
        "split": split,
        "surface_temperature_k": surface_temperature_k,
        "surface_pressure_pa": surface_pressure_pa,
        "surface_dew_point_c": surface_dew_point_c,
        "excluded_pm_ordering_rows": int(len(data) - len(physically_ordered)),
    }


def select_ridge(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    train_y: np.ndarray,
    validation_y: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Select the current Ridge alpha on validation and then predict test."""
    started = time.perf_counter()
    best_score = np.inf
    best_alpha = np.nan
    best_model: Ridge | None = None
    best_validation_prediction: np.ndarray | None = None
    for alpha in RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(train_x, train_y)
        validation_prediction = model.predict(validation_x)
        score = float(
            regression_metric_arrays(
                validation_y,
                validation_prediction,
                denominators,
            ).normalized_rmse.mean()
        )
        if score < best_score:
            best_score = score
            best_alpha = alpha
            best_model = model
            best_validation_prediction = validation_prediction
    if best_model is None or best_validation_prediction is None:
        raise RuntimeError("Ridge validation search did not select a model")
    test_prediction = best_model.predict(test_x)
    return (
        best_validation_prediction,
        test_prediction,
        float(best_alpha),
        time.perf_counter() - started,
    )


def fit_elastic_net(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    normalized_train_y: np.ndarray,
    center: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit the validation selected configuration frozen before this study."""
    started = time.perf_counter()
    model = MultiTaskElasticNet(**ELASTIC_NET_CONFIG)
    model.fit(train_x, normalized_train_y)
    validation_prediction = center + model.predict(validation_x) * denominators
    test_prediction = center + model.predict(test_x) * denominators
    return validation_prediction, test_prediction, time.perf_counter() - started


def fit_histogram_boosting(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    normalized_train_y: np.ndarray,
    center: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[int], float]:
    """Fit the frozen targetwise histogram boosting configuration."""
    started = time.perf_counter()
    validation_scaled = np.empty((len(validation_x), len(REPORT_TARGETS)), dtype=float)
    test_scaled = np.empty((len(test_x), len(REPORT_TARGETS)), dtype=float)
    iterations: list[int] = []
    for target_index in range(len(REPORT_TARGETS)):
        model = HistGradientBoostingRegressor(
            **HISTOGRAM_BOOSTING_CONFIG,
            random_state=PRIMARY_NOISE_SEED + target_index,
        )
        model.fit(train_x, normalized_train_y[:, target_index])
        validation_scaled[:, target_index] = model.predict(validation_x)
        test_scaled[:, target_index] = model.predict(test_x)
        iterations.append(int(model.n_iter_))
    return (
        center + validation_scaled * denominators,
        center + test_scaled * denominators,
        iterations,
        time.perf_counter() - started,
    )


def fit_exploratory_pca_knn(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    normalized_train_y: np.ndarray,
    center: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit the frozen PCA and KNN component used by the exploratory composite."""
    started = time.perf_counter()
    pca = PCA(
        n_components=PCA_KNN_CONFIG["pca_components"],
        svd_solver=PCA_KNN_CONFIG["pca_solver"],
        random_state=PRIMARY_NOISE_SEED,
    )
    train_pca = pca.fit_transform(train_x)
    validation_pca = pca.transform(validation_x)
    test_pca = pca.transform(test_x)
    model = KNeighborsRegressor(
        n_neighbors=PCA_KNN_CONFIG["n_neighbors"],
        weights=PCA_KNN_CONFIG["weights"],
        p=PCA_KNN_CONFIG["p"],
        n_jobs=-1,
    )
    model.fit(train_pca, normalized_train_y)
    validation_prediction = center + model.predict(validation_pca) * denominators
    test_prediction = center + model.predict(test_pca) * denominators
    return validation_prediction, test_prediction, time.perf_counter() - started


def fit_exploratory_targetwise_ridge(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    train_y: np.ndarray,
    validation_y: np.ndarray,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, list[float], float]:
    """Select one expanded grid Ridge alpha per target on validation only."""
    started = time.perf_counter()
    models: dict[float, Ridge] = {}
    validation_predictions: dict[float, np.ndarray] = {}
    validation_scores = []
    for alpha_value in EXPLORATORY_TARGET_RIDGE_ALPHAS:
        alpha = float(alpha_value)
        model = Ridge(alpha=alpha)
        model.fit(train_x, train_y)
        prediction = model.predict(validation_x)
        models[alpha] = model
        validation_predictions[alpha] = prediction
        validation_scores.append(
            regression_metric_arrays(
                validation_y,
                prediction,
                denominators,
            ).normalized_rmse
        )
    score_matrix = np.vstack(validation_scores)
    selected_indices = np.argmin(score_matrix, axis=0)
    selected_alphas = [
        float(EXPLORATORY_TARGET_RIDGE_ALPHAS[index]) for index in selected_indices
    ]
    validation_prediction = np.column_stack(
        [
            validation_predictions[alpha][:, target_index]
            for target_index, alpha in enumerate(selected_alphas)
        ]
    )
    unique_test_predictions = {
        alpha: models[alpha].predict(test_x) for alpha in set(selected_alphas)
    }
    test_prediction = np.column_stack(
        [
            unique_test_predictions[alpha][:, target_index]
            for target_index, alpha in enumerate(selected_alphas)
        ]
    )
    return (
        validation_prediction,
        test_prediction,
        selected_alphas,
        time.perf_counter() - started,
    )


def append_metric_rows(
    rows: list[dict[str, object]],
    *,
    noise_seed: int,
    model_name: str,
    model_role: str,
    configuration_status: str,
    validation_truth: np.ndarray,
    validation_prediction: np.ndarray,
    test_truth: np.ndarray,
    test_prediction: np.ndarray,
    denominators: np.ndarray,
    configuration_by_target: list[dict[str, object]],
    runtime_seconds: float,
    selected_components: tuple[str, ...] | None = None,
) -> None:
    """Append one detailed metric row per target."""
    validation_metrics = regression_metric_arrays(
        validation_truth,
        validation_prediction,
        denominators,
    )
    test_metrics = regression_metric_arrays(test_truth, test_prediction, denominators)
    for target_index, target_name in enumerate(REPORT_TARGETS):
        selected_component = (
            selected_components[target_index] if selected_components is not None else ""
        )
        rows.append(
            {
                "noise_seed": noise_seed,
                "model": model_name,
                "model_role": model_role,
                "configuration_status": configuration_status,
                "target": target_name,
                "normalization_q05_q95_range_ug_m3": float(denominators[target_index]),
                "validation_rmse_ug_m3": float(validation_metrics.rmse[target_index]),
                "validation_normalized_rmse": float(
                    validation_metrics.normalized_rmse[target_index]
                ),
                "validation_r2": float(validation_metrics.r2[target_index]),
                "test_rmse_ug_m3": float(test_metrics.rmse[target_index]),
                "test_normalized_rmse": float(test_metrics.normalized_rmse[target_index]),
                "test_r2": float(test_metrics.r2[target_index]),
                "test_bias_ug_m3": float(test_metrics.bias[target_index]),
                "configuration_json": json.dumps(
                    configuration_by_target[target_index],
                    sort_keys=True,
                ),
                "selected_for_exploratory_composite": bool(
                    selected_components is not None and selected_component == model_name
                ),
                "selected_component_model": selected_component,
                "model_runtime_seconds": runtime_seconds,
            }
        )


def run_seed(
    noise_seed: int,
    signal: np.ndarray,
    variance: np.ndarray,
    targets: np.ndarray,
    split,
    denominators: np.ndarray,
) -> list[dict[str, object]]:
    """Fit frozen candidates for one receiver noise realization."""
    rng = np.random.default_rng(noise_seed)
    observations = signal + rng.normal(scale=np.sqrt(variance), size=signal.shape)
    scaler = StandardScaler()
    train_x = scaler.fit_transform(observations[split.train])
    validation_x = scaler.transform(observations[split.validation])
    test_x = scaler.transform(observations[split.test])
    train_y = targets[split.train]
    validation_y = targets[split.validation]
    test_y = targets[split.test]
    center = train_y.mean(axis=0)
    normalized_train_y = (train_y - center) / denominators

    rows: list[dict[str, object]] = []
    mean_validation = np.broadcast_to(center, validation_y.shape)
    mean_test = np.broadcast_to(center, test_y.shape)
    append_metric_rows(
        rows,
        noise_seed=noise_seed,
        model_name="training_period_mean",
        model_role="baseline",
        configuration_status="fixed_training_only",
        validation_truth=validation_y,
        validation_prediction=mean_validation,
        test_truth=test_y,
        test_prediction=mean_test,
        denominators=denominators,
        configuration_by_target=[{"estimator": "training_target_mean"}] * len(REPORT_TARGETS),
        runtime_seconds=0.0,
    )

    ridge_validation, ridge_test, ridge_alpha, ridge_runtime = select_ridge(
        train_x,
        validation_x,
        test_x,
        train_y,
        validation_y,
        denominators,
    )
    elastic_validation, elastic_test, elastic_runtime = fit_elastic_net(
        train_x,
        validation_x,
        test_x,
        normalized_train_y,
        center,
        denominators,
    )
    hgb_validation, hgb_test, hgb_iterations, hgb_runtime = fit_histogram_boosting(
        train_x,
        validation_x,
        test_x,
        normalized_train_y,
        center,
        denominators,
    )
    knn_validation, knn_test, knn_runtime = fit_exploratory_pca_knn(
        train_x,
        validation_x,
        test_x,
        normalized_train_y,
        center,
        denominators,
    )
    (
        target_ridge_validation,
        target_ridge_test,
        target_ridge_alphas,
        target_ridge_runtime,
    ) = fit_exploratory_targetwise_ridge(
        train_x,
        validation_x,
        test_x,
        train_y,
        validation_y,
        denominators,
    )

    validation_candidates = {
        "histogram_gradient_boosting_frozen": hgb_validation,
        "exploratory_pca_knn_component": knn_validation,
        "exploratory_targetwise_ridge_component": target_ridge_validation,
        "multitask_elastic_net_frozen": elastic_validation,
    }
    test_candidates = {
        "histogram_gradient_boosting_frozen": hgb_test,
        "exploratory_pca_knn_component": knn_test,
        "exploratory_targetwise_ridge_component": target_ridge_test,
        "multitask_elastic_net_frozen": elastic_test,
    }
    selected_components = select_models_per_target(
        validation_y,
        validation_candidates,
        denominators,
        COMPOSITE_CANDIDATE_ORDER,
    )
    composite_validation = compose_per_target_predictions(
        selected_components,
        validation_candidates,
    )
    composite_test = compose_per_target_predictions(selected_components, test_candidates)

    model_specs = [
        (
            "ridge_validation_selected",
            "confirmatory_reference",
            "validation_selected_per_noise_seed",
            ridge_validation,
            ridge_test,
            [{"alpha": ridge_alpha, "alpha_grid": list(RIDGE_ALPHAS)}] * len(REPORT_TARGETS),
            ridge_runtime,
        ),
        (
            "multitask_elastic_net_frozen",
            "confirmatory_candidate",
            "frozen_before_noise_seed_stability_study",
            elastic_validation,
            elastic_test,
            [ELASTIC_NET_CONFIG] * len(REPORT_TARGETS),
            elastic_runtime,
        ),
        (
            "histogram_gradient_boosting_frozen",
            "confirmatory_candidate",
            "frozen_before_noise_seed_stability_study",
            hgb_validation,
            hgb_test,
            [
                {
                    **HISTOGRAM_BOOSTING_CONFIG,
                    "random_state": PRIMARY_NOISE_SEED + target_index,
                    "fitted_iterations": hgb_iterations[target_index],
                }
                for target_index in range(len(REPORT_TARGETS))
            ],
            hgb_runtime,
        ),
        (
            "exploratory_pca_knn_component",
            "exploratory_component",
            "frozen_before_noise_seed_stability_study",
            knn_validation,
            knn_test,
            [{**PCA_KNN_CONFIG, "random_state": PRIMARY_NOISE_SEED}] * len(REPORT_TARGETS),
            knn_runtime,
        ),
        (
            "exploratory_targetwise_ridge_component",
            "exploratory_component",
            "validation_selected_per_target_per_noise_seed",
            target_ridge_validation,
            target_ridge_test,
            [
                {
                    "alpha": target_ridge_alphas[target_index],
                    "alpha_grid": list(EXPLORATORY_TARGET_RIDGE_ALPHAS),
                }
                for target_index in range(len(REPORT_TARGETS))
            ],
            target_ridge_runtime,
        ),
    ]
    for (
        model_name,
        model_role,
        configuration_status,
        validation_prediction,
        test_prediction,
        configuration_by_target,
        runtime_seconds,
    ) in model_specs:
        append_metric_rows(
            rows,
            noise_seed=noise_seed,
            model_name=model_name,
            model_role=model_role,
            configuration_status=configuration_status,
            validation_truth=validation_y,
            validation_prediction=validation_prediction,
            test_truth=test_y,
            test_prediction=test_prediction,
            denominators=denominators,
            configuration_by_target=configuration_by_target,
            runtime_seconds=runtime_seconds,
            selected_components=selected_components,
        )

    append_metric_rows(
        rows,
        noise_seed=noise_seed,
        model_name="exploratory_validation_selected_composite",
        model_role="exploratory_composite_not_confirmatory",
        configuration_status="validation_selected_per_target_from_predeclared_components",
        validation_truth=validation_y,
        validation_prediction=composite_validation,
        test_truth=test_y,
        test_prediction=composite_test,
        denominators=denominators,
        configuration_by_target=[
            {
                "selected_component": selected_components[target_index],
                "candidate_order": list(COMPOSITE_CANDIDATE_ORDER),
                "exploratory_only": True,
            }
            for target_index in range(len(REPORT_TARGETS))
        ],
        runtime_seconds=0.0,
        selected_components=selected_components,
    )
    return rows


def overall_summary_row(summary: pd.DataFrame, model_name: str) -> pd.Series:
    """Return the unique overall summary row for a model."""
    rows = summary.loc[
        (summary["model"] == model_name)
        & (summary["aggregation"] == "overall_mean_across_targets")
    ]
    if len(rows) != 1:
        raise ValueError(f"Expected one overall summary row for {model_name}")
    return rows.iloc[0]


def dependency_versions() -> dict[str, str]:
    """Return relevant installed dependency versions."""
    versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "hitran-api"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def main() -> None:
    """Execute the frozen stability study and write auditable artifacts."""
    args = parse_args()
    started = time.perf_counter()
    for path in (args.air_quality, args.hitran_lines):
        if not path.exists():
            raise FileNotFoundError(f"Required input does not exist: {path}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detailed_path = args.output_dir / "spectral_model_stability_detailed.csv"
    summary_path = args.output_dir / "spectral_model_stability_summary.csv"
    manifest_path = args.output_dir / "spectral_model_stability_manifest.json"

    air_sha256 = sha256_file(args.air_quality)
    hitran_sha256 = sha256_file(args.hitran_lines)
    print("Loading real UCI labels and processed HITRAN line parameters.")
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    hitran = pd.read_csv(args.hitran_lines)
    print("Building the frozen 24 layer attenuation signal matrix.")
    study = prepare_study_arrays(data, hitran)
    split = study["split"]
    targets = np.asarray(study["targets"], dtype=float)
    denominators = np.asarray(study["denominators"], dtype=float)

    detailed_rows: list[dict[str, object]] = []
    for noise_seed in NOISE_SEEDS:
        seed_started = time.perf_counter()
        seed_rows = run_seed(
            noise_seed,
            np.asarray(study["signal"], dtype=float),
            np.asarray(study["variance"], dtype=float),
            targets,
            split,
            denominators,
        )
        detailed_rows.extend(seed_rows)
        seed_frame = pd.DataFrame(seed_rows)
        seed_overall = (
            seed_frame.groupby("model")["test_normalized_rmse"].mean().to_dict()
        )
        print(
            f"Seed {noise_seed}: Ridge {seed_overall[REFERENCE_MODEL]:.9f}, "
            f"ElasticNet {seed_overall['multitask_elastic_net_frozen']:.9f}, "
            f"HistGB {seed_overall['histogram_gradient_boosting_frozen']:.9f}, "
            f"exploratory composite "
            f"{seed_overall['exploratory_validation_selected_composite']:.9f} "
            f"in {time.perf_counter() - seed_started:.2f} s"
        )

    detailed = pd.DataFrame(detailed_rows)
    expected_detail_rows = len(NOISE_SEEDS) * 7 * len(REPORT_TARGETS)
    if len(detailed) != expected_detail_rows:
        raise RuntimeError(
            f"Expected {expected_detail_rows} detailed rows but produced {len(detailed)}"
        )
    summary = summarize_stability_metrics(
        detailed,
        reference_model=REFERENCE_MODEL,
        primary_seed=PRIMARY_NOISE_SEED,
    )

    primary_ridge = overall_summary_row(summary, REFERENCE_MODEL)[
        "primary_seed_test_normalized_rmse"
    ]
    exact_input_match = (
        air_sha256 == EXPECTED_AIR_SHA256 and hitran_sha256 == EXPECTED_HITRAN_SHA256
    )
    reproduction_error = float(primary_ridge - EXPECTED_PRIMARY_RIDGE_TEST_NRMSE)
    if exact_input_match and not np.isclose(
        primary_ridge,
        EXPECTED_PRIMARY_RIDGE_TEST_NRMSE,
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError(
            "The primary seed Ridge result does not reproduce the frozen benchmark: "
            f"observed {primary_ridge:.15f}, expected "
            f"{EXPECTED_PRIMARY_RIDGE_TEST_NRMSE:.15f}"
        )

    detailed.to_csv(detailed_path, index=False)
    summary.to_csv(summary_path, index=False)
    ridge_overall = overall_summary_row(summary, REFERENCE_MODEL)
    elastic_overall = overall_summary_row(summary, "multitask_elastic_net_frozen")
    hgb_overall = overall_summary_row(summary, "histogram_gradient_boosting_frozen")
    composite_overall = overall_summary_row(
        summary,
        "exploratory_validation_selected_composite",
    )
    required_wins = 8
    stability_results = {}
    for name, row in (
        ("multitask_elastic_net_frozen", elastic_overall),
        ("histogram_gradient_boosting_frozen", hgb_overall),
    ):
        mean_delta = float(row["mean_test_delta_vs_reference"])
        wins = int(row["test_seed_wins_vs_reference"])
        stability_results[name] = {
            "mean_test_normalized_rmse": float(row["mean_test_normalized_rmse"]),
            "mean_test_delta_vs_ridge": mean_delta,
            "test_seed_wins_vs_ridge": wins,
            "passes_predeclared_stability_rule": bool(
                mean_delta < 0.0 and wins >= required_wins
            ),
        }
    stable_candidates = [
        name
        for name, result in stability_results.items()
        if result["passes_predeclared_stability_rule"]
    ]

    manifest = {
        "study_status": "spectral only receiver noise stability study with simulated attenuation observations",
        "purpose": "Test whether frozen nonlinear or multitask estimators improve robustly over the current validation selected Ridge reference.",
        "inputs": {
            "air_quality_path": str(args.air_quality.resolve()),
            "air_quality_sha256": air_sha256,
            "air_quality_rows": int(len(data)),
            "hitran_path": str(args.hitran_lines.resolve()),
            "hitran_sha256": hitran_sha256,
            "hitran_lines": int(len(hitran)),
            "exact_frozen_input_hash_match": exact_input_match,
        },
        "data_scope": {
            "labels": "real UCI Beijing station pollutant measurements",
            "spectroscopy": "real processed HITRAN line parameters",
            "observations": "simulated sub THz excess attenuation plus modeled receiver noise",
            "measured_sub_thz_csi_used": False,
            "spectral_only_features": True,
            "meteorology_or_time_features_used_by_estimators": False,
        },
        "sampling": {
            "filter": "PM10_ug_m3 >= PM2_5_ug_m3",
            "sort": ["datetime", "station"],
            "selection": "20,000 deterministic linearly spaced row indices",
            "sample_rows": SAMPLE_SIZE,
            "excluded_pm_ordering_rows": study["excluded_pm_ordering_rows"],
        },
        "chronological_split": {
            "method": "complete timestamp groups with 60 percent train, 20 percent validation, and 20 percent test",
            "train_rows": int(len(split.train)),
            "validation_rows": int(len(split.validation)),
            "test_rows": int(len(split.test)),
            "train_end": str(split.train_end),
            "validation_end": str(split.validation_end),
        },
        "target_normalization": {
            "definition": "training Q95 minus training Q05 for each target",
            "targets": list(REPORT_TARGETS),
            "denominators_ug_m3": {
                target: float(denominators[index])
                for index, target in enumerate(REPORT_TARGETS)
            },
        },
        "physical_forward_model": {
            "frequency_min_ghz": 60.0,
            "frequency_max_ghz": 400.0,
            "frequency_count": N_FREQUENCIES,
            "elevation_deg": ELEVATION_DEG,
            "n_layers": 24,
            "top_altitude_m": 12_000.0,
            "pollutant_scale_height_m": 1_500.0,
            "water_scale_height_m": 2_000.0,
            "pm_scale_height_m": 1_000.0,
            "surface_temperature_k": study["surface_temperature_k"],
            "surface_pressure_pa": study["surface_pressure_pa"],
            "surface_dew_point_c": study["surface_dew_point_c"],
        },
        "reference_link": asdict(baseline_link_config()),
        "receiver_noise": {
            "noise_seeds": list(NOISE_SEEDS),
            "primary_reproduction_seed": PRIMARY_NOISE_SEED,
            "n_pilots": N_PILOTS,
            "independent_residual_error_std_db": RESIDUAL_ERROR_STD_DB,
            "generation_order": "one full 20,000 by 256 Gaussian matrix per seed before chronological indexing",
        },
        "predeclared_models": {
            "ridge_validation_selected": {
                "role": "confirmatory reference",
                "alpha_grid": list(RIDGE_ALPHAS),
                "selection": "minimum validation mean normalized RMSE separately for each noise seed",
            },
            "multitask_elastic_net_frozen": {
                "role": "confirmatory candidate",
                "configuration": ELASTIC_NET_CONFIG,
                "selection_origin": "selected in the prior primary seed exploratory validation search and frozen before this ten seed study",
                "target_scaling": "training mean centered and divided by training Q05 to Q95 range",
            },
            "histogram_gradient_boosting_frozen": {
                "role": "confirmatory candidate",
                "configuration": HISTOGRAM_BOOSTING_CONFIG,
                "per_target_random_states": [
                    PRIMARY_NOISE_SEED + index for index in range(len(REPORT_TARGETS))
                ],
                "selection_origin": "selected in the prior primary seed exploratory validation search and frozen before this ten seed study",
                "fit_mode": "one target specific estimator per pollutant",
            },
        },
        "exploratory_composite": {
            "status": "exploratory only and excluded from the confirmatory stability conclusion",
            "candidate_order_for_ties": list(COMPOSITE_CANDIDATE_ORDER),
            "pca_knn_configuration": PCA_KNN_CONFIG,
            "targetwise_ridge_alpha_grid": list(EXPLORATORY_TARGET_RIDGE_ALPHAS),
            "selection": "minimum validation normalized RMSE separately for every target and noise seed",
            "multiplicity_caveat": "The component set follows a broad primary seed search and may overfit validation through repeated comparisons.",
        },
        "test_policy": {
            "configuration_selection_uses_test": False,
            "ridge_and_composite_selection_surface": "validation only",
            "fixed_candidate_test_prediction": "computed after the candidate configuration was frozen",
            "discarded_ridge_grid_test_predictions": "not computed",
            "test_reuse_caveat": "This chronological test window was already reported by the physical feasibility study, so this is a robustness extension rather than a new pristine confirmatory period.",
        },
        "stability_rule": {
            "scope": "confirmatory candidates only",
            "definition": "mean test normalized RMSE below Ridge and wins against Ridge on at least 8 of 10 fixed noise seeds",
            "required_seed_wins": required_wins,
        },
        "primary_seed_reproduction": {
            "expected_ridge_test_mean_normalized_rmse": EXPECTED_PRIMARY_RIDGE_TEST_NRMSE,
            "observed_ridge_test_mean_normalized_rmse": float(primary_ridge),
            "absolute_error": abs(reproduction_error),
            "verified": bool(
                exact_input_match
                and np.isclose(
                    primary_ridge,
                    EXPECTED_PRIMARY_RIDGE_TEST_NRMSE,
                    rtol=0.0,
                    atol=1e-12,
                )
            ),
        },
        "headline_results": {
            "ridge_mean_test_normalized_rmse": float(
                ridge_overall["mean_test_normalized_rmse"]
            ),
            "ridge_test_std_across_noise_seeds": float(
                ridge_overall["std_test_normalized_rmse_across_seeds"]
            ),
            "confirmatory_candidate_stability": stability_results,
            "stable_confirmatory_candidates": stable_candidates,
            "exploratory_composite_mean_test_normalized_rmse": float(
                composite_overall["mean_test_normalized_rmse"]
            ),
            "exploratory_composite_seed_wins_vs_ridge": int(
                composite_overall["test_seed_wins_vs_reference"]
            ),
            "conclusion": (
                "At least one frozen candidate satisfies the predeclared stability rule."
                if stable_candidates
                else (
                    "Neither the frozen nonlinear candidate nor the frozen multitask "
                    "candidate satisfies the predeclared stability rule; estimator "
                    "complexity does not provide a stable spectral only improvement "
                    "over Ridge."
                )
            ),
        },
        "outputs": {
            "detailed_csv": str(detailed_path.resolve()),
            "detailed_csv_sha256": sha256_file(detailed_path),
            "summary_csv": str(summary_path.resolve()),
            "summary_csv_sha256": sha256_file(summary_path),
            "detailed_rows": int(len(detailed)),
            "summary_rows": int(len(summary)),
        },
        "dependency_versions": dependency_versions(),
        "runtime_seconds": time.perf_counter() - started,
        "known_limitations": [
            "No measured paired sub THz CSI is used.",
            "The ten seeds vary only the modeled independent receiver noise, not the real labels, atmosphere, link geometry, or chronological split.",
            "The same previously reported chronological test period is reused for stability reporting.",
            "The exploratory composite has validation multiplicity and must not be presented as confirmatory.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Detailed metrics: {detailed_path}")
    print(f"Summary metrics: {summary_path}")
    print(f"Manifest: {manifest_path}")
    print(manifest["headline_results"]["conclusion"])


if __name__ == "__main__":
    main()
