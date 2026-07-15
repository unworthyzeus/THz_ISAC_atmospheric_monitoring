"""Test validation-selected improvements to the fixed same-time THz inversion.

Every candidate preserves the original 20,000 rows, chronological split, six
labels, and training Q05 to Q95 denominators. Probe and power design use only
physics and training statistics. The final test block is never used to select a
context model, likelihood, probe set, power allocation, constraint, or target
noise scale.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for import_path in (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from run_rmse_metric_audit import (  # noqa: E402
    REPORT_TARGETS,
    build_context,
    resolve_input_path,
    sha256_file,
)
from thz_isac.advanced_thz_inversion import (  # noqa: E402
    bayesian_macro_posterior_risk,
    linear_gaussian_posterior_mean_with_row_priors,
    optimize_bayesian_power_fractions,
    project_out_linear_nuisance,
    regularize_covariance,
    select_bayesian_a_optimal_indices,
    select_target_balanced_information_indices,
)
from thz_isac.estimation_bounds import (  # noqa: E402
    pilot_averaged_attenuation_variance_from_snr_db,
)
from thz_isac.linear_gaussian import (  # noqa: E402
    MultiTargetRegressionMetrics,
    coherent_csi_attenuation_variance_db2,
    multi_target_regression_metrics,
    select_largest_positive_scale_below_target,
)
from thz_isac.link_budget import (  # noqa: E402
    LEOLinkBudgetConfig,
    compute_leo_link_budget,
)
from thz_isac.probe_design import (  # noqa: E402
    select_d_optimal_indices,
    uniform_probe_indices,
)


WEATHER_COLUMNS = (
    "temperature_c",
    "pressure_hpa",
    "dew_point_c",
    "rain_mm",
    "wind_speed_m_s",
)
CATEGORICAL_COLUMNS = (
    "station",
    "month_category",
    "hour_category",
    "dow_category",
)
CYCLIC_COLUMNS = (
    "doy_sin",
    "doy_cos",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
)
CONTEXT_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0)
TONE_COUNTS = (16, 32, 64, 128)
PROBE_METHODS = (
    "uniform",
    "physics_d_optimal",
    "prior_d_optimal",
    "bayesian_a_optimal",
    "target_balanced",
)
TARGET_MACRO_NRMSE = 0.03
POWER_TONE_COUNT = 32


@dataclass(frozen=True)
class ContextPriorFit:
    """Validation-selected context means and training-only residual covariance."""

    validation_means: np.ndarray
    test_means: np.ndarray
    residual_covariance: np.ndarray
    selected_alpha: float
    validation_rows: list[dict[str, object]]


@dataclass(frozen=True)
class PriorCase:
    """One fixed Gaussian prior used by candidate observation designs."""

    name: str
    validation_means: np.ndarray
    test_means: np.ndarray
    covariance: np.ndarray
    uses_context: bool


@dataclass(frozen=True)
class AttemptSpec:
    """One predeclared same-time inversion candidate."""

    case_id: str
    prior: PriorCase
    likelihood: str
    likelihood_family: str
    claim_class: str
    probe_method: str
    tone_count: int
    indices: np.ndarray
    variance: np.ndarray
    snr_linear: np.ndarray
    power_fractions: np.ndarray
    power_status: str
    nuisance_projection: bool
    nonnegative_constraint: bool
    optimizer_success: bool | None
    optimizer_accepted: bool | None
    optimizer_equal_risk: float | None
    optimizer_final_risk: float | None


def parse_args() -> argparse.Namespace:
    """Parse reproducible advanced inversion options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--physical-config",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables" / "physical_feasibility_config.json",
    )
    parser.add_argument("--air-quality", type=Path, default=None)
    parser.add_argument("--hitran-lines", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "results" / "tables",
    )
    parser.add_argument("--target-nrmse", type=float, default=TARGET_MACRO_NRMSE)
    return parser.parse_args()


def calendar_weather_features(sample: pd.DataFrame) -> pd.DataFrame:
    """Build same-time context without current or past pollutant values."""
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


def context_transformer() -> ColumnTransformer:
    """Return a fresh training-only context transformer."""
    numeric_columns = [*CYCLIC_COLUMNS, *WEATHER_COLUMNS]
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        [
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                list(CATEGORICAL_COLUMNS),
            ),
            ("numeric", numeric, numeric_columns),
        ]
    )


def fit_context_prior(context) -> ContextPriorFit:
    """Select a context Ridge mean on validation and estimate covariance on train."""
    frame = calendar_weather_features(context.sample)
    train = context.split.train
    validation = context.split.validation
    test = context.split.test
    target_mean = np.mean(context.targets[train], axis=0)
    scaled_targets = (context.targets - target_mean) / context.denominators

    transformer = context_transformer()
    train_x = transformer.fit_transform(frame.iloc[train])
    validation_x = transformer.transform(frame.iloc[validation])
    test_x = transformer.transform(frame.iloc[test])
    best_score = np.inf
    best_alpha = np.nan
    best_validation = None
    best_test = None
    validation_rows: list[dict[str, object]] = []
    for alpha in CONTEXT_ALPHAS:
        model = Ridge(alpha=alpha)
        model.fit(train_x, scaled_targets[train])
        validation_prediction = (
            model.predict(validation_x) * context.denominators + target_mean
        )
        score = multi_target_regression_metrics(
            context.targets[validation],
            validation_prediction,
            context.denominators,
        ).macro_normalized_rmse
        validation_rows.append(
            {
                "attempt_type": "context_prior_alpha",
                "case_id": f"context_prior_alpha_{alpha:g}",
                "validation_macro_normalized_rmse": score,
                "selected_on_validation": False,
                "reason": "Context alpha candidate using training-fitted preprocessing only.",
            }
        )
        if score < best_score:
            best_score = score
            best_alpha = float(alpha)
            best_validation = validation_prediction
            best_test = model.predict(test_x) * context.denominators + target_mean
    if best_validation is None or best_test is None:
        raise AssertionError("Context prior grid produced no candidate")
    for row in validation_rows:
        row["selected_on_validation"] = bool(
            row["case_id"] == f"context_prior_alpha_{best_alpha:g}"
        )

    oof_prediction = np.empty_like(context.targets[train])
    splitter = KFold(n_splits=5, shuffle=False)
    for fit_positions, held_positions in splitter.split(train):
        fit_indices = train[fit_positions]
        held_indices = train[held_positions]
        fold_transformer = context_transformer()
        fit_x = fold_transformer.fit_transform(frame.iloc[fit_indices])
        held_x = fold_transformer.transform(frame.iloc[held_indices])
        model = Ridge(alpha=best_alpha)
        model.fit(fit_x, scaled_targets[fit_indices])
        oof_prediction[held_positions] = (
            model.predict(held_x) * context.denominators + target_mean
        )
    residuals = context.targets[train] - oof_prediction
    covariance = regularize_covariance(
        np.cov(residuals, rowvar=False, ddof=1),
        relative_eigenvalue_floor=1.0e-9,
    )
    return ContextPriorFit(
        validation_means=best_validation,
        test_means=best_test,
        residual_covariance=covariance,
        selected_alpha=best_alpha,
        validation_rows=validation_rows,
    )


def likelihood_variance(
    likelihood_family: str,
    snr_linear: np.ndarray,
    n_pilots: int,
    residual_std_db: float,
) -> np.ndarray:
    """Evaluate one declared diagonal likelihood."""
    snr = np.asarray(snr_linear, dtype=float)
    if likelihood_family == "pilot_power":
        return pilot_averaged_attenuation_variance_from_snr_db(
            10.0 * np.log10(snr),
            n_pilots,
            residual_std_db,
        )
    if likelihood_family == "coherent_csi":
        return coherent_csi_attenuation_variance_db2(
            snr,
            n_pilots,
            residual_std_db,
        )
    raise ValueError(f"Unknown likelihood family: {likelihood_family}")


def all_candidate_snr(
    context,
    physical_config: dict[str, object],
    frequency_ghz: np.ndarray,
    active_count: int,
) -> np.ndarray:
    """Return equal-power SNR for every candidate if active_count tones are used."""
    base = LEOLinkBudgetConfig(**physical_config["reference_link"])
    link_config = replace(base, n_active_subcarriers=active_count)
    elevation = float(physical_config["observation"]["elevation_deg"])
    link = compute_leo_link_budget(
        frequency_ghz,
        elevation,
        link_config,
        atmospheric_loss_db=context.background_db,
    )
    snr_db = np.clip(link.snr_db[0], -150.0, 150.0)
    return 10.0 ** (snr_db / 10.0)


def select_probe_indices(
    method: str,
    context,
    variance: np.ndarray,
    count: int,
    prior_covariance: np.ndarray,
) -> np.ndarray:
    """Select probes from physics and training statistics only."""
    if method == "uniform":
        return uniform_probe_indices(context.report_design.shape[0], count)
    if method == "physics_d_optimal":
        return select_d_optimal_indices(
            context.report_design,
            variance,
            count,
            regularization=1.0e-9,
            normalize_columns=True,
        )
    if method == "prior_d_optimal":
        cholesky = np.linalg.cholesky(prior_covariance)
        return select_d_optimal_indices(
            context.report_design @ cholesky,
            variance,
            count,
            regularization=1.0e-9,
            normalize_columns=False,
        )
    if method == "bayesian_a_optimal":
        return select_bayesian_a_optimal_indices(
            context.report_design,
            variance,
            count,
            prior_covariance,
            context.denominators,
        )
    if method == "target_balanced":
        return select_target_balanced_information_indices(
            context.report_design,
            variance,
            count,
            np.sqrt(np.diag(prior_covariance)),
        )
    raise ValueError(f"Unknown probe method: {method}")


def append_constraint_variants(
    specifications: list[AttemptSpec],
    specification: AttemptSpec,
) -> None:
    """Add the raw candidate and a predeclared nonnegative context variant."""
    specifications.append(specification)
    if specification.prior.uses_context:
        specifications.append(
            AttemptSpec(
                **{
                    **specification.__dict__,
                    "case_id": f"{specification.case_id}__nonnegative",
                    "nonnegative_constraint": True,
                }
            )
        )


def build_attempt_specs(
    context,
    physical_config: dict[str, object],
    frequency_ghz: np.ndarray,
    priors: tuple[PriorCase, ...],
) -> tuple[list[AttemptSpec], list[dict[str, object]]]:
    """Freeze every physical candidate before reading test labels."""
    observation = physical_config["observation"]
    n_pilots = int(observation["n_pilots"])
    reference_residual = float(observation["residual_error_std_db"])
    likelihoods = (
        (
            "pilot_power_residual",
            "pilot_power",
            reference_residual,
            "declared_reference_likelihood",
        ),
        (
            "coherent_csi_residual",
            "coherent_csi",
            reference_residual,
            "unvalidated_likelihood_sensitivity",
        ),
        (
            "coherent_csi_zero_residual",
            "coherent_csi",
            0.0,
            "optimistic_zero_residual_sensitivity",
        ),
    )
    specifications: list[AttemptSpec] = []
    optimizer_rows: list[dict[str, object]] = []
    for prior in priors:
        for likelihood, family, residual, claim_class in likelihoods:
            for tone_count in (*TONE_COUNTS, context.report_design.shape[0]):
                snr_all = all_candidate_snr(
                    context,
                    physical_config,
                    frequency_ghz,
                    tone_count,
                )
                variance_all = likelihood_variance(
                    family,
                    snr_all,
                    n_pilots,
                    residual,
                )
                methods = PROBE_METHODS if tone_count < len(frequency_ghz) else ("uniform",)
                for method in methods:
                    indices = select_probe_indices(
                        method,
                        context,
                        variance_all,
                        tone_count,
                        prior.covariance,
                    )
                    case_id = (
                        f"{prior.name}__{likelihood}__{method}__k{tone_count}"
                    )
                    specification = AttemptSpec(
                        case_id=case_id,
                        prior=prior,
                        likelihood=likelihood,
                        likelihood_family=family,
                        claim_class=claim_class,
                        probe_method=method,
                        tone_count=tone_count,
                        indices=indices,
                        variance=variance_all[indices],
                        snr_linear=snr_all[indices],
                        power_fractions=np.full(tone_count, 1.0 / tone_count),
                        power_status="equal",
                        nuisance_projection=False,
                        nonnegative_constraint=False,
                        optimizer_success=None,
                        optimizer_accepted=None,
                        optimizer_equal_risk=None,
                        optimizer_final_risk=None,
                    )
                    append_constraint_variants(specifications, specification)

            tone_count = POWER_TONE_COUNT
            equal_snr_all = all_candidate_snr(
                context,
                physical_config,
                frequency_ghz,
                tone_count,
            )
            equal_variance_all = likelihood_variance(
                family,
                equal_snr_all,
                n_pilots,
                residual,
            )
            indices = select_probe_indices(
                "bayesian_a_optimal",
                context,
                equal_variance_all,
                tone_count,
                prior.covariance,
            )
            equal_snr = equal_snr_all[indices]

            def variance_for_fractions(fractions: np.ndarray) -> np.ndarray:
                adjusted_snr = equal_snr * tone_count * fractions
                return likelihood_variance(
                    family,
                    adjusted_snr,
                    n_pilots,
                    residual,
                )

            power_configurations = (
                (
                    "power_unbounded",
                    {"minimum_relative_to_equal": 1.0e-3},
                    f"{claim_class}+correlation_concentrated_power_sensitivity",
                ),
                (
                    "power_bounded_4x",
                    {
                        "minimum_relative_to_equal": 0.1,
                        "maximum_relative_to_equal": 4.0,
                    },
                    claim_class,
                ),
            )
            for power_label, power_options, power_claim_class in power_configurations:
                allocation = optimize_bayesian_power_fractions(
                    context.report_design[indices],
                    variance_for_fractions,
                    prior.covariance,
                    context.denominators,
                    **power_options,
                )
                adjusted_snr = equal_snr * tone_count * allocation.fractions
                optimized_variance = likelihood_variance(
                    family,
                    adjusted_snr,
                    n_pilots,
                    residual,
                )
                optimizer_rows.append(
                    {
                        "prior": prior.name,
                        "likelihood": likelihood,
                        "power_configuration": power_label,
                        "optimizer_success": allocation.optimizer_success,
                        "accepted": allocation.accepted,
                        "message": allocation.message,
                        "iterations": allocation.iterations,
                        "equal_power_posterior_risk": allocation.equal_power_risk,
                        "optimized_posterior_risk": allocation.optimized_risk,
                        "minimum_power_fraction": float(np.min(allocation.fractions)),
                        "maximum_power_fraction": float(np.max(allocation.fractions)),
                        "effective_tone_count": float(
                            1.0 / np.sum(allocation.fractions**2)
                        ),
                    }
                )
                power_status = (
                    f"optimized_{power_label}"
                    if allocation.accepted
                    else f"fallback_equal_{power_label}"
                )
                method_name = f"bayesian_a_optimal_{power_label}"
                specification = AttemptSpec(
                    case_id=(
                        f"{prior.name}__{likelihood}__{method_name}__k{tone_count}"
                    ),
                    prior=prior,
                    likelihood=likelihood,
                    likelihood_family=family,
                    claim_class=power_claim_class,
                    probe_method=method_name,
                    tone_count=tone_count,
                    indices=indices,
                    variance=optimized_variance,
                    snr_linear=adjusted_snr,
                    power_fractions=allocation.fractions,
                    power_status=power_status,
                    nuisance_projection=False,
                    nonnegative_constraint=False,
                    optimizer_success=allocation.optimizer_success,
                    optimizer_accepted=allocation.accepted,
                    optimizer_equal_risk=allocation.equal_power_risk,
                    optimizer_final_risk=allocation.optimized_risk,
                )
                append_constraint_variants(specifications, specification)

            full_count = len(frequency_ghz)
            full_snr = all_candidate_snr(
                context,
                physical_config,
                frequency_ghz,
                full_count,
            )
            full_variance = likelihood_variance(
                family,
                full_snr,
                n_pilots,
                residual,
            )
            nuisance_specification = AttemptSpec(
                case_id=(
                    f"{prior.name}__{likelihood}__full_offset_background_projected"
                ),
                prior=prior,
                likelihood=likelihood,
                likelihood_family=family,
                claim_class=claim_class,
                probe_method="full_offset_background_projected",
                tone_count=full_count,
                indices=np.arange(full_count),
                variance=full_variance,
                snr_linear=full_snr,
                power_fractions=np.full(full_count, 1.0 / full_count),
                power_status="equal",
                nuisance_projection=True,
                nonnegative_constraint=False,
                optimizer_success=None,
                optimizer_accepted=None,
                optimizer_equal_risk=None,
                optimizer_final_risk=None,
            )
            append_constraint_variants(specifications, nuisance_specification)
    return specifications, optimizer_rows


def prior_means_for_split(specification: AttemptSpec, split_name: str) -> np.ndarray:
    """Return fixed row-specific prior means for one evaluation split."""
    if split_name == "validation":
        return specification.prior.validation_means
    if split_name == "test":
        return specification.prior.test_means
    raise ValueError(f"Unknown split: {split_name}")


def split_indices(context, split_name: str) -> np.ndarray:
    """Return the fixed validation or test indices."""
    if split_name == "validation":
        return context.split.validation
    if split_name == "test":
        return context.split.test
    raise ValueError(f"Unknown split: {split_name}")


def predict_attempt(
    context,
    specification: AttemptSpec,
    split_name: str,
    *,
    variance_override: np.ndarray | None = None,
) -> np.ndarray:
    """Predict one frozen candidate without using evaluation labels."""
    rows = split_indices(context, split_name)
    indices = specification.indices
    variance = (
        specification.variance
        if variance_override is None
        else np.asarray(variance_override, dtype=float)
    )
    observations = (
        context.excess_attenuation[rows][:, indices]
        + context.standardized_noise[rows][:, indices] * np.sqrt(variance)[None, :]
    )
    design = context.report_design[indices]
    prior_means = prior_means_for_split(specification, split_name)
    if specification.nuisance_projection:
        nuisance = np.column_stack(
            [
                np.ones(len(indices)),
                context.background_db[indices],
            ]
        )
        projection = project_out_linear_nuisance(
            observations,
            design,
            variance,
            nuisance,
        )
        prediction = linear_gaussian_posterior_mean_with_row_priors(
            projection.observations,
            projection.design,
            projection.variance,
            prior_means,
            specification.prior.covariance,
        ).prediction
    else:
        prediction = linear_gaussian_posterior_mean_with_row_priors(
            observations,
            design,
            variance,
            prior_means,
            specification.prior.covariance,
        ).prediction
    if specification.nonnegative_constraint:
        prediction = np.maximum(prediction, 0.0)
    return prediction


def metrics_for_prediction(
    context,
    split_name: str,
    prediction: np.ndarray,
) -> MultiTargetRegressionMetrics:
    """Evaluate the fixed macro metric contract."""
    rows = split_indices(context, split_name)
    return multi_target_regression_metrics(
        context.targets[rows],
        prediction,
        context.denominators,
    )


def metric_rows(
    case_id: str,
    split_name: str,
    metrics: MultiTargetRegressionMetrics,
) -> list[dict[str, object]]:
    """Return tidy per-target and macro metric rows."""
    rows: list[dict[str, object]] = []
    for target_index, target in enumerate(REPORT_TARGETS):
        rows.append(
            {
                "case_id": case_id,
                "split": split_name,
                "target": target,
                "rmse_ug_m3": float(metrics.rmse[target_index]),
                "normalized_rmse": float(metrics.normalized_rmse[target_index]),
                "r2": float(metrics.r2[target_index]),
                "bias_ug_m3": float(metrics.bias[target_index]),
            }
        )
    rows.append(
        {
            "case_id": case_id,
            "split": split_name,
            "target": "macro",
            "rmse_ug_m3": np.nan,
            "normalized_rmse": metrics.macro_normalized_rmse,
            "r2": metrics.mean_r2,
            "bias_ug_m3": np.nan,
        }
    )
    return rows


def evaluate_attempts(
    context,
    specifications: list[AttemptSpec],
    context_fit: ContextPriorFit,
    current_ridge_test_metric: float,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, AttemptSpec],
    dict[str, MultiTargetRegressionMetrics],
    dict[str, MultiTargetRegressionMetrics],
]:
    """Evaluate validation first, freeze selections, then evaluate test."""
    attempt_rows: list[dict[str, object]] = []
    all_metric_rows: list[dict[str, object]] = []
    validation_metrics: dict[str, MultiTargetRegressionMetrics] = {}
    test_metrics: dict[str, MultiTargetRegressionMetrics] = {}
    successful_specs: dict[str, AttemptSpec] = {}

    train_mean = np.mean(context.targets[context.split.train], axis=0)
    controls = {
        "training_prior_control": (
            np.broadcast_to(train_mean, (len(context.split.validation), len(train_mean))),
            np.broadcast_to(train_mean, (len(context.split.test), len(train_mean))),
            "Training-period mean without THz observations.",
        ),
        "context_prior_control": (
            context_fit.validation_means,
            context_fit.test_means,
            "Calendar, station, and current-weather Ridge without THz observations.",
        ),
        "context_prior_control__nonnegative": (
            np.maximum(context_fit.validation_means, 0.0),
            np.maximum(context_fit.test_means, 0.0),
            "Context-only control with the predeclared nonnegative constraint.",
        ),
    }
    for case_id, (validation_prediction, test_prediction, reason) in controls.items():
        validation_result = metrics_for_prediction(
            context,
            "validation",
            validation_prediction,
        )
        test_result = metrics_for_prediction(context, "test", test_prediction)
        validation_metrics[case_id] = validation_result
        test_metrics[case_id] = test_result
        all_metric_rows.extend(metric_rows(case_id, "validation", validation_result))
        all_metric_rows.extend(metric_rows(case_id, "test", test_result))
        attempt_rows.append(
            {
                "attempt_type": "prior_control",
                "case_id": case_id,
                "prior": "context_prior" if case_id.startswith("context") else "training_prior",
                "likelihood": "none",
                "claim_class": "non_thz_control",
                "probe_method": "none",
                "tone_count": 0,
                "power_status": "none",
                "nuisance_projection": False,
                "nonnegative_constraint": case_id.endswith("nonnegative"),
                "uses_thz": False,
                "uses_context": case_id.startswith("context"),
                "uses_true_past_pollutants": False,
                "uses_test_for_selection": False,
                "validation_macro_normalized_rmse": validation_result.macro_normalized_rmse,
                "test_macro_normalized_rmse": test_result.macro_normalized_rmse,
                "validation_thz_gain_over_prior": 0.0,
                "test_thz_gain_over_prior": 0.0,
                "test_delta_vs_current_ridge": (
                    test_result.macro_normalized_rmse - current_ridge_test_metric
                ),
                "selected_roles": "",
                "status": "control",
                "reason": reason,
            }
        )

    # Selection phase. No test prediction or test metric is computed here.
    failure_messages: dict[str, str] = {}
    for specification in specifications:
        try:
            prediction = predict_attempt(context, specification, "validation")
            result = metrics_for_prediction(context, "validation", prediction)
            validation_metrics[specification.case_id] = result
            successful_specs[specification.case_id] = specification
            all_metric_rows.extend(
                metric_rows(specification.case_id, "validation", result)
            )
        except (ValueError, np.linalg.LinAlgError, RuntimeError) as exc:
            failure_messages[specification.case_id] = f"{type(exc).__name__}: {exc}"

    def select_role(role: str, predicate) -> tuple[str, AttemptSpec]:
        eligible = [
            specification
            for specification in successful_specs.values()
            if predicate(specification)
        ]
        if not eligible:
            raise AssertionError(f"No successful candidates for selection role {role}")
        selected = min(
            eligible,
            key=lambda item: (
                validation_metrics[item.case_id].macro_normalized_rmse,
                item.case_id,
            ),
        )
        return role, selected

    role_pairs = (
        select_role(
            "best_declared_training_prior",
            lambda item: item.prior.name == "training_prior"
            and item.likelihood == "pilot_power_residual",
        ),
        select_role(
            "best_training_prior_any_likelihood",
            lambda item: item.prior.name == "training_prior",
        ),
        select_role(
            "best_training_prior_residual_retaining",
            lambda item: item.prior.name == "training_prior"
            and item.likelihood != "coherent_csi_zero_residual",
        ),
        select_role(
            "best_training_prior_equal_power",
            lambda item: item.prior.name == "training_prior"
            and item.power_status == "equal",
        ),
        select_role(
            "best_training_prior_bounded_or_equal_power",
            lambda item: item.prior.name == "training_prior"
            and "power_unbounded" not in item.power_status,
        ),
        select_role(
            "best_context_assisted",
            lambda item: item.prior.name == "context_prior",
        ),
        select_role(
            "best_context_bounded_or_equal_power",
            lambda item: item.prior.name == "context_prior"
            and "power_unbounded" not in item.power_status,
        ),
        select_role(
            "best_residual_retaining_any_prior",
            lambda item: item.likelihood != "coherent_csi_zero_residual",
        ),
        select_role("best_overall_single_snapshot", lambda item: True),
    )
    selected_by_role = dict(role_pairs)
    roles_by_case: dict[str, list[str]] = {}
    for role, specification in role_pairs:
        roles_by_case.setdefault(specification.case_id, []).append(role)

    # Evaluation phase. Selections above are frozen before test predictions exist.
    for case_id, specification in successful_specs.items():
        prediction = predict_attempt(context, specification, "test")
        result = metrics_for_prediction(context, "test", prediction)
        test_metrics[case_id] = result
        all_metric_rows.extend(metric_rows(case_id, "test", result))

    for specification in specifications:
        case_id = specification.case_id
        if case_id in failure_messages:
            attempt_rows.append(
                {
                    "attempt_type": "thz_inversion",
                    "case_id": case_id,
                    "prior": specification.prior.name,
                    "likelihood": specification.likelihood,
                    "claim_class": specification.claim_class,
                    "probe_method": specification.probe_method,
                    "tone_count": specification.tone_count,
                    "power_status": specification.power_status,
                    "nuisance_projection": specification.nuisance_projection,
                    "nonnegative_constraint": specification.nonnegative_constraint,
                    "uses_thz": True,
                    "uses_context": specification.prior.uses_context,
                    "uses_true_past_pollutants": False,
                    "uses_test_for_selection": False,
                    "validation_macro_normalized_rmse": np.nan,
                    "test_macro_normalized_rmse": np.nan,
                    "validation_thz_gain_over_prior": np.nan,
                    "test_thz_gain_over_prior": np.nan,
                    "test_delta_vs_current_ridge": np.nan,
                    "selected_roles": "",
                    "status": "execution_failed",
                    "reason": failure_messages[case_id],
                }
            )
            continue

        validation_result = validation_metrics[case_id]
        test_result = test_metrics[case_id]
        if specification.prior.uses_context:
            control_id = (
                "context_prior_control__nonnegative"
                if specification.nonnegative_constraint
                else "context_prior_control"
            )
        else:
            control_id = "training_prior_control"
        validation_gain = (
            validation_metrics[control_id].macro_normalized_rmse
            - validation_result.macro_normalized_rmse
        )
        test_gain = (
            test_metrics[control_id].macro_normalized_rmse
            - test_result.macro_normalized_rmse
        )
        if test_gain > 1.0e-6:
            status = "thz_increment_improved"
        elif test_gain < -1.0e-6:
            status = "worse_than_prior_control"
        else:
            status = "no_resolved_thz_increment"

        reason_parts = [
            f"Validation-only case selection; test THz gain over its prior control is {test_gain:.9g}."
        ]
        if specification.prior.uses_context:
            reason_parts.append(
                "Absolute improvement versus the spectral baseline is dominated by the same-time context prior."
            )
        if "optimistic_zero_residual_sensitivity" in specification.claim_class:
            reason_parts.append(
                "This assumes the independent residual error is exactly zero."
            )
        elif "unvalidated_likelihood_sensitivity" in specification.claim_class:
            reason_parts.append(
                "The coherent CSI delta-method likelihood is not receiver-validated."
            )
        if specification.nuisance_projection:
            reason_parts.append(
                "Offset and background columns are projected out although the simulator injects neither nuisance."
            )
        if specification.power_status.startswith("optimized"):
            reason_parts.append(
                "Power allocation reduced training-prior posterior risk at fixed total power."
            )
        elif specification.power_status.startswith("fallback_equal"):
            reason_parts.append(
                "The power optimizer found no accepted risk reduction and retained equal power."
            )
        if "power_unbounded" in specification.power_status:
            reason_parts.append(
                "The weakly bounded optimizer may concentrate nearly all power on one tone and exploit training target correlations rather than spectrally resolve every target."
            )

        attempt_rows.append(
            {
                "attempt_type": "thz_inversion",
                "case_id": case_id,
                "prior": specification.prior.name,
                "likelihood": specification.likelihood,
                "claim_class": specification.claim_class,
                "probe_method": specification.probe_method,
                "tone_count": specification.tone_count,
                "power_status": specification.power_status,
                "nuisance_projection": specification.nuisance_projection,
                "nonnegative_constraint": specification.nonnegative_constraint,
                "uses_thz": True,
                "uses_context": specification.prior.uses_context,
                "uses_true_past_pollutants": False,
                "uses_test_for_selection": False,
                "validation_macro_normalized_rmse": validation_result.macro_normalized_rmse,
                "test_macro_normalized_rmse": test_result.macro_normalized_rmse,
                "validation_thz_gain_over_prior": validation_gain,
                "test_thz_gain_over_prior": test_gain,
                "test_delta_vs_current_ridge": (
                    test_result.macro_normalized_rmse - current_ridge_test_metric
                ),
                "selected_roles": ";".join(sorted(roles_by_case.get(case_id, []))),
                "status": status,
                "reason": " ".join(reason_parts),
            }
        )
    return (
        attempt_rows,
        all_metric_rows,
        selected_by_role,
        validation_metrics,
        test_metrics,
    )


def information_eigenvalues(
    context,
    specification: AttemptSpec,
    variance: np.ndarray,
) -> np.ndarray:
    """Return prior-whitened measurement-information eigenvalues."""
    design = context.report_design[specification.indices]
    if specification.nuisance_projection:
        nuisance = np.column_stack(
            [
                np.ones(specification.tone_count),
                context.background_db[specification.indices],
            ]
        )
        projection = project_out_linear_nuisance(
            np.zeros((1, specification.tone_count)),
            design,
            variance,
            nuisance,
        )
        fisher = projection.design.T @ projection.design
    else:
        fisher = design.T @ (design / variance[:, None])
    cholesky = np.linalg.cholesky(specification.prior.covariance)
    return np.linalg.eigvalsh(cholesky.T @ fisher @ cholesky)


def posterior_risk_at_scale(
    context,
    specification: AttemptSpec,
    scale: float,
) -> float:
    """Return training-prior Bayesian risk at a common noise scale."""
    variance = specification.variance * scale**2
    design = context.report_design[specification.indices]
    if specification.nuisance_projection:
        nuisance = np.column_stack(
            [
                np.ones(specification.tone_count),
                context.background_db[specification.indices],
            ]
        )
        projection = project_out_linear_nuisance(
            np.zeros((1, specification.tone_count)),
            design,
            variance,
            nuisance,
        )
        return bayesian_macro_posterior_risk(
            projection.design,
            projection.variance,
            specification.prior.covariance,
            context.denominators,
        )
    return bayesian_macro_posterior_risk(
        design,
        variance,
        specification.prior.covariance,
        context.denominators,
    )


def information_budget_scale(
    context,
    specification: AttemptSpec,
    target_nrmse: float,
) -> float | None:
    """Return the largest common noise scale meeting a Bayesian risk target."""
    base = posterior_risk_at_scale(context, specification, 1.0)
    if base <= target_nrmse:
        return 1.0
    lower = 1.0e-10
    if posterior_risk_at_scale(context, specification, lower) > target_nrmse:
        return None
    selection = select_largest_positive_scale_below_target(
        lambda scale: posterior_risk_at_scale(context, specification, scale),
        target_nrmse,
        lower,
        1.0,
        iterations=45,
    )
    return selection.selected_scale


def select_information_budget_cases(
    context,
    specifications: list[AttemptSpec],
    targets: tuple[float, ...],
) -> tuple[list[tuple[str, float, AttemptSpec]], list[dict[str, object]]]:
    """Select minimum expected repeat cases using training-only posterior risk."""
    base_candidates = [
        item for item in specifications if not item.nonnegative_constraint
    ]
    categories = (
        (
            "minimum_declared_training_prior_information_budget",
            lambda item: item.prior.name == "training_prior"
            and item.likelihood == "pilot_power_residual",
        ),
        (
            "minimum_residual_training_prior_information_budget",
            lambda item: item.prior.name == "training_prior"
            and item.likelihood != "coherent_csi_zero_residual",
        ),
        (
            "minimum_optimistic_training_prior_information_budget",
            lambda item: item.prior.name == "training_prior",
        ),
        (
            "minimum_context_assisted_information_budget",
            lambda item: item.prior.name == "context_prior",
        ),
    )
    selected: list[tuple[str, float, AttemptSpec]] = []
    screening_rows: list[dict[str, object]] = []
    for target in targets:
        for category, predicate in categories:
            candidates = [item for item in base_candidates if predicate(item)]
            scales = []
            for specification in candidates:
                scale = information_budget_scale(context, specification, target)
                if scale is not None:
                    scales.append((scale, specification.case_id, specification))
            if not scales:
                raise AssertionError(
                    f"No information-budget candidate can reach {target} for {category}"
                )
            scale, _, winner = min(scales, key=lambda item: (-item[0], item[1]))
            role = f"{category}_target_{target:.3f}"
            selected.append((role, target, winner))
            screening_rows.append(
                {
                    "selection_role": role,
                    "target_macro_normalized_rmse": target,
                    "case_id": winner.case_id,
                    "training_only_expected_noise_std_factor": scale,
                    "training_only_expected_repeat_equivalent": 1.0 / scale**2,
                    "candidate_count": len(candidates),
                    "selection_basis": (
                        "minimum expected repeat from training-only Gaussian posterior risk"
                    ),
                }
            )
    return selected, screening_rows


def target_requirement(
    context,
    specification: AttemptSpec,
    target_nrmse: float,
    n_pilots: int,
    role: str,
) -> dict[str, object]:
    """Select an ideal independent-repeat scale on validation only."""

    def scaled_metric(scale: float, split_name: str) -> float:
        prediction = predict_attempt(
            context,
            specification,
            split_name,
            variance_override=specification.variance * scale**2,
        )
        return metrics_for_prediction(
            context,
            split_name,
            prediction,
        ).macro_normalized_rmse

    base_validation = scaled_metric(1.0, "validation")
    if base_validation <= target_nrmse:
        selected_scale = 1.0
        validation_metric = base_validation
        selection_iterations = 0
        feasible = True
    else:
        lower = 1.0e-8
        lower_metric = scaled_metric(lower, "validation")
        if lower_metric > target_nrmse:
            lower = 1.0e-12
            lower_metric = scaled_metric(lower, "validation")
        if lower_metric > target_nrmse:
            return {
                "selection_role": role,
                "case_id": specification.case_id,
                "status": "target_unattainable_under_global_scaling",
                "target_macro_normalized_rmse": target_nrmse,
                "base_validation_macro_normalized_rmse": base_validation,
                "lowest_scale_checked": lower,
                "lowest_scale_validation_macro_normalized_rmse": lower_metric,
            }
        selection = select_largest_positive_scale_below_target(
            lambda scale: scaled_metric(scale, "validation"),
            target_nrmse,
            lower,
            1.0,
            iterations=50,
        )
        selected_scale = selection.selected_scale
        validation_metric = selection.selected_metric
        selection_iterations = selection.iterations
        feasible = True

    test_metric = scaled_metric(selected_scale, "test")
    repeat_equivalent = 1.0 / selected_scale**2
    zero_residual_variance = likelihood_variance(
        specification.likelihood_family,
        specification.snr_linear,
        n_pilots,
        0.0,
    )
    zero_residual_validation_prediction = predict_attempt(
        context,
        specification,
        "validation",
        variance_override=zero_residual_variance,
    )
    zero_residual_validation = metrics_for_prediction(
        context,
        "validation",
        zero_residual_validation_prediction,
    ).macro_normalized_rmse
    zero_residual_status = (
        "target_met_by_residual_removal_alone"
        if zero_residual_validation <= target_nrmse
        else "target_unattainable_by_residual_removal_alone"
    )
    base_eigenvalues = information_eigenvalues(
        context,
        specification,
        specification.variance,
    )
    required_eigenvalues = base_eigenvalues / selected_scale**2
    return {
        "selection_role": role,
        "case_id": specification.case_id,
        "status": "validation_selected_global_noise_scale" if feasible else "infeasible",
        "target_macro_normalized_rmse": target_nrmse,
        "base_validation_macro_normalized_rmse": base_validation,
        "selected_noise_standard_deviation_factor": selected_scale,
        "required_noise_standard_deviation_reduction": 1.0 / selected_scale,
        "ideal_independent_repeat_equivalent": repeat_equivalent,
        "ideal_repeat_count_ceiling": int(np.ceil(repeat_equivalent)),
        "ideal_pilot_symbol_equivalent": repeat_equivalent * n_pilots,
        "validation_macro_normalized_rmse_at_selected_scale": validation_metric,
        "test_macro_normalized_rmse_at_selected_scale": test_metric,
        "selection_iterations": selection_iterations,
        "zero_residual_validation_macro_normalized_rmse": zero_residual_validation,
        "zero_residual_status": zero_residual_status,
        "base_prior_whitened_information_min_eigenvalue": float(
            np.min(base_eigenvalues)
        ),
        "base_prior_whitened_information_max_eigenvalue": float(
            np.max(base_eigenvalues)
        ),
        "required_prior_whitened_information_min_eigenvalue": float(
            np.min(required_eigenvalues)
        ),
        "required_prior_whitened_information_max_eigenvalue": float(
            np.max(required_eigenvalues)
        ),
        "claim_boundary": (
            "The repeat equivalent scales every diagonal error component and is valid "
            "only for independent stationary repeats with exact forward physics."
        ),
    }


def probe_rows(
    frequency_ghz: np.ndarray,
    specifications: list[AttemptSpec],
) -> list[dict[str, object]]:
    """Record every selected frequency and power fraction."""
    rows: list[dict[str, object]] = []
    for specification in specifications:
        for rank, (index, variance, snr, fraction) in enumerate(
            zip(
                specification.indices,
                specification.variance,
                specification.snr_linear,
                specification.power_fractions,
                strict=True,
            ),
            start=1,
        ):
            rows.append(
                {
                    "case_id": specification.case_id,
                    "selection_rank": rank,
                    "frequency_index": int(index),
                    "frequency_ghz": float(frequency_ghz[index]),
                    "power_fraction": float(fraction),
                    "snr_db": float(10.0 * np.log10(snr)),
                    "noise_variance_db2": float(variance),
                }
            )
    return rows


def main() -> None:
    """Run the fixed-contract advanced inversion study."""
    args = parse_args()
    if not args.physical_config.exists():
        raise FileNotFoundError(f"Missing physical config: {args.physical_config}")
    if not np.isfinite(args.target_nrmse) or args.target_nrmse <= 0.0:
        raise ValueError("target_nrmse must be strictly positive")
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
    for path, expected_hash in (
        (air_quality_path, physical_config["inputs"]["air_quality_sha256"]),
        (hitran_path, physical_config["inputs"]["hitran_sha256"]),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing hashed input: {path}")
        if sha256_file(path) != expected_hash:
            raise ValueError(f"Input hash differs from the fixed benchmark: {path}")

    audit_manifest_path = (
        PROJECT_ROOT / "results" / "tables" / "rmse_metric_audit_manifest.json"
    )
    with audit_manifest_path.open("r", encoding="utf-8") as handle:
        audit_manifest = json.load(handle)
    current_ridge_metric = float(
        audit_manifest["reproduction"]["reproduced_ridge_macro_normalized_rmse"]
    )

    print("Loading hashed real labels and spectroscopy, then rebuilding the fixed sample.")
    data = pd.read_csv(air_quality_path, parse_dates=["datetime"])
    hitran = pd.read_csv(hitran_path)
    context = build_context(data, hitran, physical_config)
    frequency_ghz = np.linspace(
        float(physical_config["atmosphere"]["frequency_min_ghz"]),
        float(physical_config["atmosphere"]["frequency_max_ghz"]),
        int(physical_config["atmosphere"]["frequency_count"]),
    )

    print("Selecting the same-time calendar, station, and weather prior on validation.")
    context_fit = fit_context_prior(context)
    train_targets = context.targets[context.split.train]
    train_mean = np.mean(train_targets, axis=0)
    train_covariance = regularize_covariance(
        np.cov(train_targets, rowvar=False, ddof=1)
    )
    priors = (
        PriorCase(
            name="training_prior",
            validation_means=np.broadcast_to(
                train_mean,
                (len(context.split.validation), len(train_mean)),
            ),
            test_means=np.broadcast_to(
                train_mean,
                (len(context.split.test), len(train_mean)),
            ),
            covariance=train_covariance,
            uses_context=False,
        ),
        PriorCase(
            name="context_prior",
            validation_means=context_fit.validation_means,
            test_means=context_fit.test_means,
            covariance=context_fit.residual_covariance,
            uses_context=True,
        ),
    )

    print("Freezing physics, likelihood, probe, power, constraint, and nuisance cases.")
    specifications, optimizer_rows = build_attempt_specs(
        context,
        physical_config,
        frequency_ghz,
        priors,
    )
    print(f"Evaluating {len(specifications)} frozen THz candidates on validation first.")
    (
        attempt_rows,
        metrics,
        selected_by_role,
        validation_metrics,
        test_metrics,
    ) = evaluate_attempts(
        context,
        specifications,
        context_fit,
        current_ridge_metric,
    )
    attempt_rows = [*context_fit.validation_rows, *attempt_rows]

    baseline_case = "training_prior__pilot_power_residual__uniform__k256"
    expected_lmmse = float(
        audit_manifest["pilot_variance_sensitivity"]["pilot_power_residual"][
            "physics_lmmse_macro_normalized_rmse"
        ]
    )
    observed_lmmse = test_metrics[baseline_case].macro_normalized_rmse
    if abs(observed_lmmse - expected_lmmse) > 1.0e-12:
        raise AssertionError("The advanced branch did not reproduce the audited LMMSE")

    print("Selecting ideal repeat requirements on validation for 0.08 and 0.03.")
    n_pilots = int(physical_config["observation"]["n_pilots"])
    requirement_roles = (
        "best_declared_training_prior",
        "best_training_prior_residual_retaining",
        "best_training_prior_equal_power",
        "best_training_prior_bounded_or_equal_power",
        "best_training_prior_any_likelihood",
        "best_overall_single_snapshot",
    )
    requirement_targets = tuple(sorted({0.08, float(args.target_nrmse)}, reverse=True))
    requirements = [
        target_requirement(
            context,
            selected_by_role[role],
            target,
            n_pilots,
            role,
        )
        for role in requirement_roles
        for target in requirement_targets
    ]
    budget_cases, information_screening = select_information_budget_cases(
        context,
        specifications,
        requirement_targets,
    )
    screening_by_role = {
        row["selection_role"]: row for row in information_screening
    }
    for role, target, specification in budget_cases:
        requirement = target_requirement(
            context,
            specification,
            target,
            n_pilots,
            role,
        )
        requirement["training_only_expected_noise_std_factor"] = screening_by_role[
            role
        ]["training_only_expected_noise_std_factor"]
        requirement["training_only_expected_repeat_equivalent"] = screening_by_role[
            role
        ]["training_only_expected_repeat_equivalent"]
        requirement["configuration_selection_basis"] = screening_by_role[role][
            "selection_basis"
        ]
        requirements.append(requirement)

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    attempts_path = output_dir / "advanced_thz_inversion_attempts.csv"
    metrics_path = output_dir / "advanced_thz_inversion_metrics.csv"
    probes_path = output_dir / "advanced_thz_inversion_probes.csv"
    optimizer_path = output_dir / "advanced_thz_inversion_power_optimization.csv"
    information_screening_path = (
        output_dir / "advanced_thz_inversion_information_budget_screening.csv"
    )
    requirements_path = output_dir / "advanced_thz_inversion_requirements.csv"
    manifest_path = output_dir / "advanced_thz_inversion_manifest.json"
    pd.DataFrame(attempt_rows).to_csv(attempts_path, index=False)
    pd.DataFrame(metrics).to_csv(metrics_path, index=False)
    pd.DataFrame(probe_rows(frequency_ghz, specifications)).to_csv(
        probes_path,
        index=False,
    )
    pd.DataFrame(optimizer_rows).to_csv(optimizer_path, index=False)
    pd.DataFrame(information_screening).to_csv(
        information_screening_path,
        index=False,
    )
    pd.DataFrame(requirements).to_csv(requirements_path, index=False)

    selected_summary = {}
    for role, specification in selected_by_role.items():
        selected_summary[role] = {
            "case_id": specification.case_id,
            "prior": specification.prior.name,
            "likelihood": specification.likelihood,
            "claim_class": specification.claim_class,
            "probe_method": specification.probe_method,
            "tone_count": specification.tone_count,
            "power_status": specification.power_status,
            "nuisance_projection": specification.nuisance_projection,
            "nonnegative_constraint": specification.nonnegative_constraint,
            "validation_macro_normalized_rmse": validation_metrics[
                specification.case_id
            ].macro_normalized_rmse,
            "test_macro_normalized_rmse": test_metrics[
                specification.case_id
            ].macro_normalized_rmse,
        }

    dependency_versions = {}
    for package in ("numpy", "pandas", "scipy", "scikit-learn", "hitran-api"):
        try:
            dependency_versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            dependency_versions[package] = "not installed"
    source_module = PROJECT_ROOT / "src" / "thz_isac" / "advanced_thz_inversion.py"
    test_file = PROJECT_ROOT / "tests" / "test_advanced_thz_inversion.py"
    manifest = {
        "study_status": "fixed-contract advanced same-time THz inversion diagnostic",
        "metric_definition": {
            "per_target": "RMSE divided by the fixed training Q95 minus Q05 span",
            "headline": "unweighted macro mean across the same six pollutant targets",
            "targets": list(REPORT_TARGETS),
            "target_macro_normalized_rmse_values": list(requirement_targets),
        },
        "evaluation_contract": {
            "sample_rows": len(context.sample),
            "sample_indices_sha256": hashlib.sha256(
                context.sample_indices.astype(np.int64).tobytes()
            ).hexdigest(),
            "train_rows": len(context.split.train),
            "validation_rows": len(context.split.validation),
            "test_rows": len(context.split.test),
            "train_end": str(context.split.train_end),
            "validation_end": str(context.split.validation_end),
            "denominators_ug_m3": {
                target: float(value)
                for target, value in zip(
                    REPORT_TARGETS,
                    context.denominators,
                    strict=True,
                )
            },
            "labels_changed": False,
            "rows_changed": False,
            "split_changed": False,
            "denominators_changed": False,
        },
        "inputs": {
            "air_quality_path": str(air_quality_path),
            "air_quality_sha256": sha256_file(air_quality_path),
            "hitran_path": str(hitran_path),
            "hitran_sha256": sha256_file(hitran_path),
            "physical_config_path": str(args.physical_config.resolve()),
            "physical_config_sha256": sha256_file(args.physical_config),
            "rmse_audit_manifest_path": str(audit_manifest_path.resolve()),
            "rmse_audit_manifest_sha256": sha256_file(audit_manifest_path),
        },
        "selection_policy": {
            "context_alpha": "validation macro normalized RMSE only",
            "probe_selection": (
                "physics and training-only prior covariance or training denominators; "
                "never validation or test labels"
            ),
            "power_allocation": "training-only Gaussian posterior risk",
            "case_selection": "validation macro normalized RMSE only",
            "target_noise_scale": "validation macro normalized RMSE only",
            "minimum_repeat_configuration": (
                "minimum expected repeat from training-only Gaussian posterior risk; "
                "the exact common noise scale is then selected on validation"
            ),
            "test_policy": (
                "selected case identifiers were frozen before any test prediction or test "
                "metric was computed"
            ),
            "test_based_selection": False,
            "true_past_pollutant_features": False,
            "current_pollutant_feature_leakage": False,
        },
        "context_prior": {
            "features": [
                "station",
                "calendar categories and cycles",
                *WEATHER_COLUMNS,
            ],
            "selected_alpha": context_fit.selected_alpha,
            "covariance": (
                "five-fold training-only out-of-fold residual covariance after validation "
                "selected alpha"
            ),
            "uses_true_past_pollutants": False,
            "claim_boundary": (
                "This is context-assisted same-time estimation, not satellite-only THz "
                "retrieval."
            ),
        },
        "attempt_inventory": {
            "thz_candidate_count": len(specifications),
            "context_alpha_candidate_count": len(context_fit.validation_rows),
            "execution_failure_count": int(
                sum(row.get("status") == "execution_failed" for row in attempt_rows)
            ),
            "probe_methods": list(PROBE_METHODS),
            "tone_counts": [*TONE_COUNTS, len(frequency_ghz)],
            "likelihoods": [
                "pilot_power_residual",
                "coherent_csi_residual",
                "coherent_csi_zero_residual",
            ],
        },
        "reproduction": {
            "current_ridge_test_macro_normalized_rmse": current_ridge_metric,
            "audited_training_prior_lmmse_test_macro_normalized_rmse": expected_lmmse,
            "advanced_branch_reproduced_lmmse_test_macro_normalized_rmse": observed_lmmse,
            "absolute_difference": abs(observed_lmmse - expected_lmmse),
        },
        "selected_cases": selected_summary,
        "target_requirements": requirements,
        "artifacts": {
            "attempts_csv": str(attempts_path),
            "attempts_sha256": sha256_file(attempts_path),
            "metrics_csv": str(metrics_path),
            "metrics_sha256": sha256_file(metrics_path),
            "probes_csv": str(probes_path),
            "probes_sha256": sha256_file(probes_path),
            "power_optimization_csv": str(optimizer_path),
            "power_optimization_sha256": sha256_file(optimizer_path),
            "information_budget_screening_csv": str(information_screening_path),
            "information_budget_screening_sha256": sha256_file(
                information_screening_path
            ),
            "requirements_csv": str(requirements_path),
            "requirements_sha256": sha256_file(requirements_path),
        },
        "source_files": {
            "script": str(Path(__file__).resolve()),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "module": str(source_module.resolve()),
            "module_sha256": sha256_file(source_module),
            "tests": str(test_file.resolve()),
            "tests_sha256": sha256_file(test_file),
        },
        "dependency_versions": dependency_versions,
        "claim_boundaries": [
            "Every THz observation remains simulated from the fixed HITRAN forward model.",
            "The coherent CSI likelihood is a high-SNR delta-method sensitivity, not a validated receiver likelihood.",
            "Zero residual error is an optimistic sensitivity and not achieved hardware performance.",
            "Context-assisted results use real same-time weather and station identity and are not satellite-only inversion.",
            "The test period was previously reported, so this study is diagnostic rather than pristine confirmation.",
            "The ideal repeat requirement assumes independent stationary errors and exact forward physics.",
            "Weakly bounded power allocation can collapse to one effective tone and exploit training target correlations; bounded and equal-power cases are reported separately.",
            "Probe choices remain conceptual multiband points without hardware or regulatory constraints.",
            "The reference atmosphere is inherited from the existing full-data scenario medians.",
        ],
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)

    print(f"Current Ridge test macro normalized RMSE: {current_ridge_metric:.12f}")
    for role, summary in selected_summary.items():
        print(
            f"{role}: {summary['case_id']} | validation "
            f"{summary['validation_macro_normalized_rmse']:.12f} | test "
            f"{summary['test_macro_normalized_rmse']:.12f}"
        )
    for requirement in requirements:
        if "ideal_independent_repeat_equivalent" in requirement:
            print(
                f"{requirement['selection_role']} repeat equivalent to reach "
                f"{requirement['target_macro_normalized_rmse']:.4f}: "
                f"{requirement['ideal_independent_repeat_equivalent']:.6g}"
            )
        else:
            print(
                f"{requirement['selection_role']} target status: "
                f"{requirement['status']}"
            )
    print(f"Wrote {attempts_path}")
    print(f"Wrote {metrics_path}")
    print(f"Wrote {probes_path}")
    print(f"Wrote {optimizer_path}")
    print(f"Wrote {information_screening_path}")
    print(f"Wrote {requirements_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
