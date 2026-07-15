"""Run causal context and pollutant lag baselines beside the THz inversion.

The pollutant lag models in this script are auxiliary nowcasting controls. They
assume that true past ground measurements are available and therefore must not
be interpreted as satellite only THz retrievals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_path in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from run_physical_feasibility import (  # noqa: E402
    AIR_COLUMNS,
    BASE_ELEVATION_DEG,
    BASE_N_FREQUENCIES,
    BASE_N_PILOTS,
    BASE_RESIDUAL_ERROR_STD_DB,
    RANDOM_SEED,
    REPORT_TARGETS,
    baseline_link_config,
    safe_observation_variance,
)
from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    validate_disjoint_split,
)
from thz_isac.link_budget import compute_leo_link_budget  # noqa: E402
from thz_isac.physical_spectroscopy import (  # noqa: E402
    apply_plane_parallel_slant,
    build_layered_zenith_attenuation_design,
)
from thz_isac.temporal_baselines import (  # noqa: E402
    build_exact_causal_lag_features,
    evenly_spaced_sample_indices,
)


TARGET_COLUMNS = tuple(AIR_COLUMNS[target] for target in REPORT_TARGETS)
WEATHER_COLUMNS = (
    "temperature_c",
    "pressure_hpa",
    "dew_point_c",
    "rain_mm",
    "wind_speed_m_s",
)
CATEGORICAL_COLUMNS = ("station", "month_category", "hour_category", "dow_category")
CYCLIC_COLUMNS = (
    "doy_sin",
    "doy_cos",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
)
LAG_HOURS = (1, 2, 3, 6, 24, 168)
SAMPLE_SIZE = 20_000
CALENDAR_RIDGE_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0)
SPECTRAL_RIDGE_ALPHAS = (
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
SPECTRAL_BLOCK_MULTIPLIERS = (0.0, 0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0)
HGB_CONFIGS = (
    {"max_iter": 100, "max_leaf_nodes": 15, "l2_regularization": 1.0},
    {"max_iter": 200, "max_leaf_nodes": 15, "l2_regularization": 10.0},
    {"max_iter": 200, "max_leaf_nodes": 31, "l2_regularization": 10.0},
)


def parse_args() -> argparse.Namespace:
    """Parse input paths for the reproducible auxiliary benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
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
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of one input file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mean_normalized_rmse(
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
) -> float:
    """Return target averaged RMSE normalized by training quantile spans."""
    rmse = np.sqrt(np.mean((prediction - truth) ** 2, axis=0))
    return float(np.mean(rmse / denominators))


def calendar_weather_features(sample: pd.DataFrame) -> pd.DataFrame:
    """Build calendar, station, and contemporaneous weather features."""
    timestamp = pd.to_datetime(sample["datetime"], errors="raise")
    frame = pd.DataFrame(index=sample.index)
    frame["station"] = sample["station"].astype(str)
    frame["month_category"] = timestamp.dt.month.astype(str)
    frame["hour_category"] = timestamp.dt.hour.astype(str)
    frame["dow_category"] = timestamp.dt.dayofweek.astype(str)
    frame["doy_sin"] = np.sin(2.0 * np.pi * (timestamp.dt.dayofyear - 1) / 365.25)
    frame["doy_cos"] = np.cos(2.0 * np.pi * (timestamp.dt.dayofyear - 1) / 365.25)
    frame["hour_sin"] = np.sin(2.0 * np.pi * timestamp.dt.hour / 24.0)
    frame["hour_cos"] = np.cos(2.0 * np.pi * timestamp.dt.hour / 24.0)
    frame["dow_sin"] = np.sin(2.0 * np.pi * timestamp.dt.dayofweek / 7.0)
    frame["dow_cos"] = np.cos(2.0 * np.pi * timestamp.dt.dayofweek / 7.0)
    for column in WEATHER_COLUMNS:
        frame[column] = sample[column].to_numpy(float)
    return frame


def feature_blocks(
    frame: pd.DataFrame,
    split,
    numeric_columns: list[str],
    *,
    dense: bool,
    scale_numeric: bool,
) -> tuple[np.ndarray | sparse.spmatrix, ...]:
    """Fit preprocessing on training only and transform all three periods."""
    numeric_steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy="median"))
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    transformer = ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=not dense),
                list(CATEGORICAL_COLUMNS),
            ),
            ("numeric", Pipeline(numeric_steps), numeric_columns),
        ]
    )
    train = transformer.fit_transform(frame.iloc[split.train])
    validation = transformer.transform(frame.iloc[split.validation])
    test = transformer.transform(frame.iloc[split.test])
    return train, validation, test


def fit_ridge_grid(
    train_x,
    validation_x,
    test_x,
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
    alphas: tuple[float, ...],
    model_name: str,
) -> tuple[np.ndarray, np.ndarray, float, list[dict[str, object]]]:
    """Select one multivariate Ridge alpha using validation only."""
    best_score = np.inf
    best_alpha = np.nan
    best_validation = None
    best_test = None
    selection_rows = []
    for alpha in alphas:
        model = Ridge(alpha=alpha)
        model.fit(train_x, scaled_targets[split.train])
        validation_prediction = model.predict(validation_x) * denominators + target_mean
        score = mean_normalized_rmse(
            targets[split.validation], validation_prediction, denominators
        )
        selection_rows.append(
            {
                "model": model_name,
                "candidate": json.dumps({"alpha": alpha}, sort_keys=True),
                "validation_mean_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_alpha = alpha
            best_validation = validation_prediction
            best_test = model.predict(test_x) * denominators + target_mean
    if best_validation is None or best_test is None:
        raise AssertionError("Ridge grid did not produce a candidate")
    return best_validation, best_test, float(best_alpha), selection_rows


def fit_hgb_grid(
    train_x: np.ndarray,
    validation_x: np.ndarray,
    test_x: np.ndarray,
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
    model_name: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], list[dict[str, object]]]:
    """Select a common HGB configuration on mean validation NRMSE."""
    best_score = np.inf
    best_config = None
    best_validation = None
    best_test = None
    selection_rows = []
    for config in HGB_CONFIGS:
        validation_prediction = np.empty((len(split.validation), len(TARGET_COLUMNS)))
        test_prediction = np.empty((len(split.test), len(TARGET_COLUMNS)))
        for target_index in range(len(TARGET_COLUMNS)):
            model = HistGradientBoostingRegressor(
                max_iter=int(config["max_iter"]),
                max_leaf_nodes=int(config["max_leaf_nodes"]),
                l2_regularization=float(config["l2_regularization"]),
                learning_rate=0.05,
                min_samples_leaf=20,
                early_stopping=False,
                random_state=RANDOM_SEED,
            )
            model.fit(train_x, scaled_targets[split.train, target_index])
            validation_prediction[:, target_index] = (
                model.predict(validation_x) * denominators[target_index]
                + target_mean[target_index]
            )
            test_prediction[:, target_index] = (
                model.predict(test_x) * denominators[target_index]
                + target_mean[target_index]
            )
        score = mean_normalized_rmse(
            targets[split.validation], validation_prediction, denominators
        )
        candidate = {
            **config,
            "learning_rate": 0.05,
            "min_samples_leaf": 20,
            "early_stopping": False,
        }
        selection_rows.append(
            {
                "model": model_name,
                "candidate": json.dumps(candidate, sort_keys=True),
                "validation_mean_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_config = candidate
            best_validation = validation_prediction
            best_test = test_prediction
    if best_config is None or best_validation is None or best_test is None:
        raise AssertionError("HGB grid did not produce a candidate")
    return best_validation, best_test, best_config, selection_rows


def climatology_prediction(
    sample: pd.DataFrame,
    train_indices: np.ndarray,
    prediction_indices: np.ndarray,
    fallback: np.ndarray,
) -> np.ndarray:
    """Predict from training period month and hour means with a global fallback."""
    means = (
        sample.iloc[train_indices]
        .groupby(["month", "hour"], observed=True)[list(TARGET_COLUMNS)]
        .mean()
        .reset_index()
    )
    prediction = (
        sample.iloc[prediction_indices][["month", "hour"]]
        .merge(
            means,
            on=["month", "hour"],
            how="left",
            sort=False,
            validate="many_to_one",
        )[list(TARGET_COLUMNS)]
        .to_numpy(float)
    )
    return np.where(np.isnan(prediction), fallback[None, :], prediction)


def simulate_reference_observations(
    data: pd.DataFrame,
    hitran: pd.DataFrame,
    targets: np.ndarray,
) -> np.ndarray:
    """Recreate the reference simulated THz attenuation observations."""
    frequency_ghz = np.linspace(60.0, 400.0, BASE_N_FREQUENCIES)
    design = build_layered_zenith_attenuation_design(
        hitran,
        frequency_ghz,
        surface_dew_point_c=float(data["dew_point_c"].median()),
        pollutant_scale_height_m=1_500.0,
        water_scale_height_m=2_000.0,
        pm_scale_height_m=1_000.0,
        n_layers=24,
        top_altitude_m=12_000.0,
        surface_temperature_k=float(data["temperature_c"].median() + 273.15),
        surface_pressure_pa=float(data["pressure_hpa"].median() * 100.0),
        partition_sum_version=2025,
    )
    gas_design = apply_plane_parallel_slant(design.gas_db_per_ug_m3, BASE_ELEVATION_DEG)
    pm_design = apply_plane_parallel_slant(design.pm_db_per_ug_m3, BASE_ELEVATION_DEG)
    joint_design = np.column_stack([gas_design, pm_design])
    parameters = np.column_stack([targets[:, :5], targets[:, 5] - targets[:, 4]])
    background = apply_plane_parallel_slant(design.background_db, BASE_ELEVATION_DEG)
    link = compute_leo_link_budget(
        design.frequency_ghz,
        BASE_ELEVATION_DEG,
        baseline_link_config(BASE_N_FREQUENCIES),
        atmospheric_loss_db=background,
    )
    variance = safe_observation_variance(
        link.snr_db[0], BASE_N_PILOTS, BASE_RESIDUAL_ERROR_STD_DB
    )
    signal = parameters @ joint_design.T
    noise = np.random.default_rng(RANDOM_SEED).normal(
        scale=np.sqrt(variance), size=signal.shape
    )
    return signal + noise


def fit_spectral_ridge(
    observations: np.ndarray,
    targets: np.ndarray,
    split,
    denominators: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, list[dict[str, object]]]:
    """Reproduce the current simulated THz Ridge benchmark."""
    scaler = StandardScaler()
    train_x = scaler.fit_transform(observations[split.train])
    validation_x = scaler.transform(observations[split.validation])
    test_x = scaler.transform(observations[split.test])
    best_score = np.inf
    best_alpha = np.nan
    best_validation = None
    best_test = None
    rows = []
    for alpha in SPECTRAL_RIDGE_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(train_x, targets[split.train])
        validation_prediction = model.predict(validation_x)
        score = mean_normalized_rmse(
            targets[split.validation], validation_prediction, denominators
        )
        rows.append(
            {
                "model": "simulated THz spectral Ridge",
                "candidate": json.dumps({"alpha": alpha}, sort_keys=True),
                "validation_mean_normalized_rmse": score,
            }
        )
        if score < best_score:
            best_score = score
            best_alpha = alpha
            best_validation = validation_prediction
            best_test = model.predict(test_x)
    if best_validation is None or best_test is None:
        raise AssertionError("Spectral Ridge grid did not produce a candidate")
    return best_validation, best_test, float(best_alpha), rows


def fit_context_spectrum_ablation(
    context_blocks: tuple[sparse.spmatrix, sparse.spmatrix, sparse.spmatrix],
    observations: np.ndarray,
    scaled_targets: np.ndarray,
    targets: np.ndarray,
    split,
    target_mean: np.ndarray,
    denominators: np.ndarray,
) -> tuple[
    dict[str, tuple[np.ndarray, np.ndarray]], dict[str, object], list[dict[str, object]]
]:
    """Select context only and context plus spectrum Ridge models on validation."""
    observation_scaler = StandardScaler()
    observation_blocks = (
        observation_scaler.fit_transform(observations[split.train]),
        observation_scaler.transform(observations[split.validation]),
        observation_scaler.transform(observations[split.test]),
    )
    best_context = (np.inf, np.nan, None, None)
    best_combined = (np.inf, np.nan, np.nan, None, None)
    rows = []
    for multiplier in SPECTRAL_BLOCK_MULTIPLIERS:
        blocks = tuple(
            sparse.hstack(
                [context, sparse.csr_matrix(spectrum * multiplier)], format="csr"
            )
            for context, spectrum in zip(
                context_blocks, observation_blocks, strict=True
            )
        )
        for alpha in CALENDAR_RIDGE_ALPHAS[:-1]:
            model = Ridge(alpha=alpha)
            model.fit(blocks[0], scaled_targets[split.train])
            validation_prediction = (
                model.predict(blocks[1]) * denominators + target_mean
            )
            test_prediction = model.predict(blocks[2]) * denominators + target_mean
            score = mean_normalized_rmse(
                targets[split.validation], validation_prediction, denominators
            )
            model_name = (
                "calendar and current weather Ridge"
                if multiplier == 0.0
                else "calendar weather Ridge plus simulated THz"
            )
            rows.append(
                {
                    "model": model_name,
                    "candidate": json.dumps(
                        {"alpha": alpha, "spectral_block_multiplier": multiplier},
                        sort_keys=True,
                    ),
                    "validation_mean_normalized_rmse": score,
                }
            )
            if multiplier == 0.0 and score < best_context[0]:
                best_context = (
                    score,
                    alpha,
                    validation_prediction,
                    test_prediction,
                )
            if score < best_combined[0]:
                best_combined = (
                    score,
                    multiplier,
                    alpha,
                    validation_prediction,
                    test_prediction,
                )
    if best_context[2] is None or best_combined[3] is None:
        raise AssertionError("Context spectrum grid did not produce a candidate")
    predictions = {
        "calendar and current weather Ridge": (best_context[2], best_context[3]),
        "calendar weather Ridge plus simulated THz": (
            best_combined[3],
            best_combined[4],
        ),
    }
    selection = {
        "context_ridge_alpha": float(best_context[1]),
        "combined_ridge_alpha": float(best_combined[2]),
        "combined_spectral_block_multiplier": float(best_combined[1]),
    }
    return predictions, selection, rows


def regression_rows(
    model: str,
    split_name: str,
    truth: np.ndarray,
    prediction: np.ndarray,
    denominators: np.ndarray,
    contract: dict[str, object],
) -> list[dict[str, object]]:
    """Return auditable per target metrics for one prediction matrix."""
    rows = []
    for index, target in enumerate(REPORT_TARGETS):
        error = prediction[:, index] - truth[:, index]
        rmse = float(np.sqrt(np.mean(error**2)))
        rows.append(
            {
                "model": model,
                "split": split_name,
                **contract,
                "target": target,
                "mae_ug_m3": float(np.mean(np.abs(error))),
                "rmse_ug_m3": rmse,
                "normalized_rmse": rmse / float(denominators[index]),
                "r2": float(r2_score(truth[:, index], prediction[:, index])),
                "bias_ug_m3": float(np.mean(error)),
            }
        )
    return rows


def main() -> None:
    """Execute all auxiliary baselines and write CSV and JSON artifacts."""
    args = parse_args()
    for path in (args.air_quality, args.hitran_lines):
        if not path.exists():
            raise FileNotFoundError(f"Required input does not exist: {path}")
    table_dir = PROJECT_ROOT / "results" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    print("Loading the real Beijing labels and applying the physical PM ordering rule.")
    data = pd.read_csv(args.air_quality, parse_dates=["datetime"])
    hitran = pd.read_csv(args.hitran_lines)
    physically_ordered = (
        data.loc[data["PM10_ug_m3"] >= data["PM2_5_ug_m3"]]
        .sort_values(["datetime", "station"])
        .reset_index(drop=True)
    )
    sample_indices = evenly_spaced_sample_indices(len(physically_ordered), SAMPLE_SIZE)
    sample = physically_ordered.iloc[sample_indices].reset_index(drop=True)
    targets = sample[list(TARGET_COLUMNS)].to_numpy(float)
    metadata = sample[["datetime", "station"]]
    split = chronological_timestamp_split(metadata)
    validate_disjoint_split(split, len(sample))
    target_mean = np.mean(targets[split.train], axis=0)
    denominators = np.quantile(targets[split.train], 0.95, axis=0) - np.quantile(
        targets[split.train], 0.05, axis=0
    )
    scaled_targets = (targets - target_mean) / denominators

    print("Constructing exact causal pollutant lags and context features.")
    context = calendar_weather_features(sample)
    lag_result = build_exact_causal_lag_features(
        physically_ordered,
        sample[["datetime", "station"]],
        TARGET_COLUMNS,
        LAG_HOURS,
    )
    features = pd.concat([context, lag_result.features], axis=1)
    calendar_numeric = list(CYCLIC_COLUMNS)
    context_numeric = [*CYCLIC_COLUMNS, *WEATHER_COLUMNS]
    lag_numeric = list(context_numeric)
    for lag in LAG_HOURS:
        lag_numeric.extend(f"{column}_lag{lag}h" for column in TARGET_COLUMNS)
        lag_numeric.extend(f"{column}_lag{lag}h_missing" for column in TARGET_COLUMNS)

    metrics: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    selected: dict[str, object] = {}
    contracts = {
        "training period mean": {
            "inference_class": "constant baseline",
            "uses_current_weather": False,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": False,
        },
        "seasonal month hour climatology": {
            "inference_class": "training only seasonal prior",
            "uses_current_weather": False,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": False,
        },
        "calendar Ridge": {
            "inference_class": "calendar and station prior",
            "uses_current_weather": False,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": False,
        },
        "calendar and current weather Ridge": {
            "inference_class": "auxiliary context prior",
            "uses_current_weather": True,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": False,
        },
        "calendar and current weather HGB": {
            "inference_class": "auxiliary context prior",
            "uses_current_weather": True,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": False,
        },
        "exact one hour persistence with true past labels": {
            "inference_class": "one hour forecast with ground truth lag",
            "uses_current_weather": False,
            "uses_true_pollutant_lags": True,
            "uses_simulated_thz": False,
        },
        "multilag HGB with true past labels": {
            "inference_class": "auxiliary nowcast with ground truth lags",
            "uses_current_weather": True,
            "uses_true_pollutant_lags": True,
            "uses_simulated_thz": False,
        },
        "simulated THz spectral Ridge": {
            "inference_class": "same time simulated THz inversion",
            "uses_current_weather": False,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": True,
        },
        "calendar weather Ridge plus simulated THz": {
            "inference_class": "context plus simulated THz ablation",
            "uses_current_weather": True,
            "uses_true_pollutant_lags": False,
            "uses_simulated_thz": True,
        },
    }

    predictions: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    mean_validation = np.broadcast_to(target_mean, targets[split.validation].shape)
    mean_test = np.broadcast_to(target_mean, targets[split.test].shape)
    predictions["training period mean"] = (mean_validation, mean_test)
    predictions["seasonal month hour climatology"] = (
        climatology_prediction(sample, split.train, split.validation, target_mean),
        climatology_prediction(sample, split.train, split.test, target_mean),
    )

    calendar_blocks = feature_blocks(
        features,
        split,
        calendar_numeric,
        dense=False,
        scale_numeric=True,
    )
    calendar_validation, calendar_test, calendar_alpha, rows = fit_ridge_grid(
        *calendar_blocks,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
        CALENDAR_RIDGE_ALPHAS,
        "calendar Ridge",
    )
    predictions["calendar Ridge"] = (calendar_validation, calendar_test)
    selected["calendar_ridge_alpha"] = calendar_alpha
    validation_rows.extend(rows)

    context_dense_blocks = feature_blocks(
        features,
        split,
        context_numeric,
        dense=True,
        scale_numeric=False,
    )
    context_hgb_validation, context_hgb_test, context_hgb_config, rows = fit_hgb_grid(
        *context_dense_blocks,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
        "calendar and current weather HGB",
    )
    predictions["calendar and current weather HGB"] = (
        context_hgb_validation,
        context_hgb_test,
    )
    selected["context_hgb"] = context_hgb_config
    validation_rows.extend(rows)

    persistence = lag_result.features[
        [f"{column}_lag1h" for column in TARGET_COLUMNS]
    ].to_numpy(float)
    persistence = np.where(np.isnan(persistence), target_mean[None, :], persistence)
    predictions["exact one hour persistence with true past labels"] = (
        persistence[split.validation],
        persistence[split.test],
    )

    lag_blocks = feature_blocks(
        features,
        split,
        lag_numeric,
        dense=True,
        scale_numeric=False,
    )
    lag_validation, lag_test, lag_config, rows = fit_hgb_grid(
        *lag_blocks,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
        "multilag HGB with true past labels",
    )
    predictions["multilag HGB with true past labels"] = (lag_validation, lag_test)
    selected["multilag_hgb"] = lag_config
    selected["multilag_transformed_feature_count"] = int(lag_blocks[0].shape[1])
    validation_rows.extend(rows)

    print("Recreating the simulated THz spectrum and its context ablation.")
    observations = simulate_reference_observations(data, hitran, targets)
    spectral_validation, spectral_test, spectral_alpha, rows = fit_spectral_ridge(
        observations, targets, split, denominators
    )
    predictions["simulated THz spectral Ridge"] = (
        spectral_validation,
        spectral_test,
    )
    selected["spectral_ridge_alpha"] = spectral_alpha
    validation_rows.extend(rows)

    context_sparse_blocks = feature_blocks(
        features,
        split,
        context_numeric,
        dense=False,
        scale_numeric=True,
    )
    ablation_predictions, ablation_selection, rows = fit_context_spectrum_ablation(
        context_sparse_blocks,
        observations,
        scaled_targets,
        targets,
        split,
        target_mean,
        denominators,
    )
    predictions.update(ablation_predictions)
    selected.update(ablation_selection)
    validation_rows.extend(rows)

    model_order = list(contracts)
    for model in model_order:
        validation_prediction, test_prediction = predictions[model]
        metrics.extend(
            regression_rows(
                model,
                "validation",
                targets[split.validation],
                validation_prediction,
                denominators,
                contracts[model],
            )
        )
        metrics.extend(
            regression_rows(
                model,
                "test",
                targets[split.test],
                test_prediction,
                denominators,
                contracts[model],
            )
        )
    metrics_table = pd.DataFrame(metrics)
    metrics_path = table_dir / "auxiliary_nowcasting_metrics.csv"
    metrics_table.to_csv(metrics_path, index=False)

    summary_rows = []
    for model in model_order:
        row = {"model": model, **contracts[model]}
        for split_name in ("validation", "test"):
            subset = metrics_table.loc[
                (metrics_table["model"] == model)
                & (metrics_table["split"] == split_name)
            ]
            row[f"{split_name}_mean_normalized_rmse"] = float(
                subset["normalized_rmse"].mean()
            )
            row[f"{split_name}_mean_r2"] = float(subset["r2"].mean())
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows)
    ablation_path = table_dir / "auxiliary_nowcasting_ablation.csv"
    summary.to_csv(ablation_path, index=False)

    coverage_rows = []
    for split_name, indices in (
        ("train", split.train),
        ("validation", split.validation),
        ("test", split.test),
    ):
        for lag in LAG_HOURS:
            missing = float(
                lag_result.features.iloc[indices][
                    f"{TARGET_COLUMNS[0]}_lag{lag}h_missing"
                ].mean()
            )
            coverage_rows.append(
                {
                    "split": split_name,
                    "lag_hours": lag,
                    "missing_rate": missing,
                    "exact_match_coverage": 1.0 - missing,
                }
            )
    coverage_path = table_dir / "auxiliary_nowcasting_lag_coverage.csv"
    pd.DataFrame(coverage_rows).to_csv(coverage_path, index=False)

    validation_path = table_dir / "auxiliary_nowcasting_validation.csv"
    pd.DataFrame(validation_rows).to_csv(validation_path, index=False)

    summary_index = summary.set_index("model")
    current_rmse = float(
        summary_index.loc["simulated THz spectral Ridge", "test_mean_normalized_rmse"]
    )
    best_nowcast = float(
        summary_index.loc[
            "multilag HGB with true past labels", "test_mean_normalized_rmse"
        ]
    )
    context_only = float(
        summary_index.loc[
            "calendar and current weather Ridge", "test_mean_normalized_rmse"
        ]
    )
    context_spectrum = float(
        summary_index.loc[
            "calendar weather Ridge plus simulated THz",
            "test_mean_normalized_rmse",
        ]
    )
    manifest = {
        "study_status": "auxiliary causal context and nowcasting benchmark",
        "interpretation": {
            "primary_physical_task": "same time inversion from simulated THz attenuation",
            "pollutant_lag_task": "one step nowcasting with true past ground labels",
            "warning": (
                "Pollutant lag results are not satellite only THz retrievals and must not "
                "be presented as improved spectral identifiability."
            ),
        },
        "inputs": {
            "air_quality_path": str(args.air_quality.resolve()),
            "air_quality_sha256": sha256_file(args.air_quality),
            "hitran_path": str(args.hitran_lines.resolve()),
            "hitran_sha256": sha256_file(args.hitran_lines),
            "complete_case_rows": len(data),
            "pm_ordered_rows": len(physically_ordered),
        },
        "sample": {
            "rows": SAMPLE_SIZE,
            "rule": "np.linspace(0, n_rows - 1, 20000, dtype=int)",
            "random_seed": RANDOM_SEED,
        },
        "split": {
            "train_rows": len(split.train),
            "validation_rows": len(split.validation),
            "test_rows": len(split.test),
            "train_start": str(sample.iloc[split.train]["datetime"].min()),
            "train_end": str(split.train_end),
            "validation_start": str(sample.iloc[split.validation]["datetime"].min()),
            "validation_end": str(split.validation_end),
            "test_start": str(sample.iloc[split.test]["datetime"].min()),
            "test_end": str(sample.iloc[split.test]["datetime"].max()),
        },
        "normalization": {
            "definition": "training Q05 to Q95 target span",
            "denominators_ug_m3": {
                target: float(value)
                for target, value in zip(REPORT_TARGETS, denominators, strict=True)
            },
        },
        "features": {
            "weather_columns": list(WEATHER_COLUMNS),
            "lag_hours": list(LAG_HOURS),
            "lag_join": "same station at exactly query time minus lag",
            "missing_lag_handling": "training median imputation plus explicit missing indicators",
            "multilag_transformed_feature_count": selected[
                "multilag_transformed_feature_count"
            ],
        },
        "selection": selected,
        "headline": {
            "current_spectral_ridge_test_mean_normalized_rmse": current_rmse,
            "requested_tenfold_target": current_rmse / 10.0,
            "best_auxiliary_nowcast_test_mean_normalized_rmse": best_nowcast,
            "best_nowcast_over_requested_target": best_nowcast / (current_rmse / 10.0),
            "context_only_ridge_test_mean_normalized_rmse": context_only,
            "context_plus_spectrum_test_mean_normalized_rmse": context_spectrum,
            "spectrum_test_delta_after_context": context_spectrum - context_only,
        },
        "outputs": {
            "metrics": str(metrics_path.resolve()),
            "ablation": str(ablation_path.resolve()),
            "lag_coverage": str(coverage_path.resolve()),
            "validation_candidates": str(validation_path.resolve()),
        },
    }
    manifest_path = table_dir / "auxiliary_nowcasting_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(
        summary[["model", "test_mean_normalized_rmse", "test_mean_r2"]].to_string(
            index=False
        )
    )
    print(f"Wrote auxiliary nowcasting artifacts to {table_dir}.")


if __name__ == "__main__":
    main()
