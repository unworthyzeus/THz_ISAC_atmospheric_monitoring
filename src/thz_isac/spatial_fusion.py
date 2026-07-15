"""Leakage resistant features for contemporaneous station network reconstruction.

This module is separate from THz spectroscopy. It reconstructs one station's
current pollutant vector from other ground stations, strictly past query
station measurements, weather, station identity, and calendar context.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from thz_isac.temporal_baselines import build_exact_causal_lag_features


@dataclass(frozen=True)
class SpatialFusionFeatures:
    """Feature matrix and arrays required to audit the information contract."""

    frame: pd.DataFrame
    current_other_values: np.ndarray
    query_station_indices: np.ndarray
    donor_counts: np.ndarray
    lag_source_timestamps: pd.DataFrame
    station_order: tuple[str, ...]
    target_columns: tuple[str, ...]
    lag_hours: tuple[int, ...]
    feature_groups: Mapping[str, tuple[str, ...]]


def build_spatial_fusion_features(
    source: pd.DataFrame,
    query: pd.DataFrame,
    target_columns: Sequence[str],
    weather_columns: Sequence[str],
    lag_hours: Sequence[int],
    *,
    timestamp_column: str = "datetime",
    station_column: str = "station",
) -> SpatialFusionFeatures:
    """Build contemporaneous donor, exact lag, weather, and context features.

    At each query row, all current target values from the query station are
    replaced by missing values before any feature or aggregate is calculated.
    Exact lag values use only the same query station at ``time - lag``.
    """
    targets = tuple(target_columns)
    weather = tuple(weather_columns)
    lags = tuple(int(value) for value in lag_hours)
    if not targets:
        raise ValueError("At least one target column is required")
    if not weather:
        raise ValueError("At least one weather column is required")
    if not lags or len(set(lags)) != len(lags) or any(value <= 0 for value in lags):
        raise ValueError("Lag hours must be unique positive integers")

    required_source = {timestamp_column, station_column, *targets, *weather}
    required_query = {timestamp_column, station_column, *weather}
    missing_source = sorted(required_source.difference(source.columns))
    missing_query = sorted(required_query.difference(query.columns))
    if missing_source:
        raise ValueError(f"Source is missing columns: {missing_source}")
    if missing_query:
        raise ValueError(f"Query is missing columns: {missing_query}")

    source_frame = source[[timestamp_column, station_column, *targets, *weather]].copy()
    source_frame[timestamp_column] = pd.to_datetime(
        source_frame[timestamp_column], errors="raise"
    )
    source_frame[station_column] = source_frame[station_column].astype(str)
    if source_frame.duplicated([station_column, timestamp_column]).any():
        raise ValueError("Source station and timestamp keys must be unique")

    query_frame = query[[timestamp_column, station_column, *weather]].copy()
    query_frame[timestamp_column] = pd.to_datetime(
        query_frame[timestamp_column], errors="raise"
    )
    query_frame[station_column] = query_frame[station_column].astype(str)
    if query_frame.duplicated([station_column, timestamp_column]).any():
        raise ValueError("Query station and timestamp keys must be unique")

    stations = tuple(sorted(source_frame[station_column].unique()))
    station_to_index = {station: index for index, station in enumerate(stations)}
    unknown_stations = sorted(set(query_frame[station_column]) - set(stations))
    if unknown_stations:
        raise ValueError(f"Query contains unknown stations: {unknown_stations}")
    query_station_indices = query_frame[station_column].map(station_to_index).to_numpy(int)
    query_times = pd.DatetimeIndex(query_frame[timestamp_column])

    target_pivot = source_frame.pivot(
        index=timestamp_column,
        columns=station_column,
        values=list(targets),
    )
    target_pivot = target_pivot.reindex(
        columns=pd.MultiIndex.from_product([targets, stations])
    )
    current_other = target_pivot.reindex(query_times).to_numpy(float).reshape(
        len(query_frame), len(targets), len(stations)
    )
    row_indices = np.arange(len(query_frame))
    current_other[row_indices, :, query_station_indices] = np.nan
    donor_counts = np.sum(np.isfinite(current_other), axis=2)

    feature_columns: dict[str, np.ndarray] = {}
    feature_groups: dict[str, list[str]] = {}

    def add(group: str, name: str, values: np.ndarray) -> None:
        feature_columns[name] = np.asarray(values)
        feature_groups.setdefault(group, []).append(name)

    for target_index, target in enumerate(targets):
        for station_index, station in enumerate(stations):
            add(
                "spatial_current_pivot",
                f"current_other__{target}__{station}",
                current_other[:, target_index, station_index],
            )
        for statistic, values in _nan_statistics(current_other[:, target_index, :]).items():
            add(
                "spatial_current_aggregate",
                f"current_other__{target}__{statistic}",
                values,
            )
        add(
            "spatial_current_aggregate",
            f"current_other__{target}__donor_count",
            donor_counts[:, target_index].astype(float),
        )

    lag_result = build_exact_causal_lag_features(
        source_frame,
        query_frame,
        targets,
        lags,
        timestamp_column=timestamp_column,
        group_column=station_column,
    )
    for column in lag_result.features:
        add("query_causal_lag", column, lag_result.features[column].to_numpy())

    for lag in lags:
        lag_times = query_times - pd.Timedelta(hours=lag)
        lagged_other = target_pivot.reindex(lag_times).to_numpy(float).reshape(
            len(query_frame), len(targets), len(stations)
        )
        lagged_other[row_indices, :, query_station_indices] = np.nan
        change = current_other - lagged_other
        paired_counts = np.sum(np.isfinite(change), axis=2)
        for target_index, target in enumerate(targets):
            if lag == 1:
                for station_index, station in enumerate(stations):
                    add(
                        "spatial_change_pivot",
                        f"change_other__{target}__lag1h__{station}",
                        change[:, target_index, station_index],
                    )
            statistics = _nan_statistics(change[:, target_index, :])
            for statistic in ("mean", "median", "std"):
                add(
                    "spatial_change_aggregate",
                    f"change_other__{target}__lag{lag}h__{statistic}",
                    statistics[statistic],
                )
            add(
                "spatial_change_aggregate",
                f"change_other__{target}__lag{lag}h__donor_count",
                paired_counts[:, target_index].astype(float),
            )

    weather_pivot = source_frame.pivot(
        index=timestamp_column,
        columns=station_column,
        values=list(weather),
    ).reindex(columns=pd.MultiIndex.from_product([weather, stations]))
    current_weather_other = weather_pivot.reindex(query_times).to_numpy(float).reshape(
        len(query_frame), len(weather), len(stations)
    )
    current_weather_other[row_indices, :, query_station_indices] = np.nan
    for weather_index, column in enumerate(weather):
        add("query_weather", f"query_weather__{column}", query_frame[column].to_numpy(float))
        weather_statistics = _nan_statistics(current_weather_other[:, weather_index, :])
        for statistic in ("mean", "median", "std"):
            add(
                "network_weather",
                f"weather_other__{column}__{statistic}",
                weather_statistics[statistic],
            )

    timestamp = query_frame[timestamp_column]
    hour = timestamp.dt.hour.to_numpy(float)
    day_of_week = timestamp.dt.dayofweek.to_numpy(float)
    day_of_year = timestamp.dt.dayofyear.to_numpy(float) - 1.0
    add("calendar", "hour_sin", np.sin(2.0 * np.pi * hour / 24.0))
    add("calendar", "hour_cos", np.cos(2.0 * np.pi * hour / 24.0))
    add("calendar", "dow_sin", np.sin(2.0 * np.pi * day_of_week / 7.0))
    add("calendar", "dow_cos", np.cos(2.0 * np.pi * day_of_week / 7.0))
    add("calendar", "doy_sin", np.sin(2.0 * np.pi * day_of_year / 365.25))
    add("calendar", "doy_cos", np.cos(2.0 * np.pi * day_of_year / 365.25))
    for station_index, station in enumerate(stations):
        add(
            "station_identity",
            f"query_station__{station}",
            (query_station_indices == station_index).astype(float),
        )

    result = SpatialFusionFeatures(
        frame=pd.DataFrame(feature_columns, index=query.index),
        current_other_values=current_other,
        query_station_indices=query_station_indices,
        donor_counts=donor_counts,
        lag_source_timestamps=lag_result.source_timestamps,
        station_order=stations,
        target_columns=targets,
        lag_hours=lags,
        feature_groups={key: tuple(value) for key, value in feature_groups.items()},
    )
    assert_query_current_targets_excluded(result)
    return result


def assert_query_current_targets_excluded(features: SpatialFusionFeatures) -> None:
    """Raise if any query station current target survives masking."""
    row_indices = np.arange(len(features.frame))
    leaked = features.current_other_values[
        row_indices,
        :,
        features.query_station_indices,
    ]
    if not np.isnan(leaked).all():
        raise AssertionError("Query station current targets remain in donor values")
    for row_index, station_index in enumerate(features.query_station_indices):
        station = features.station_order[station_index]
        for target in features.target_columns:
            column = f"current_other__{target}__{station}"
            if not np.isnan(features.frame.iloc[row_index][column]):
                raise AssertionError(
                    "Query station current target remains in the pivot feature matrix"
                )
    maximum_donors = len(features.station_order) - 1
    if np.any(features.donor_counts > maximum_donors):
        raise AssertionError("Donor count includes the query station")


def other_station_mean_prediction(
    features: SpatialFusionFeatures,
    training_mean: np.ndarray,
) -> np.ndarray:
    """Return one same target mean across current donor stations."""
    fallback = _target_fallback(training_mean, len(features.target_columns))
    prediction = np.column_stack(
        [
            features.frame[f"current_other__{target}__mean"].to_numpy(float)
            for target in features.target_columns
        ]
    )
    return np.where(np.isfinite(prediction), prediction, fallback[None, :])


def lag_delta_transfer_prediction(
    features: SpatialFusionFeatures,
    lag_hours: int,
    training_mean: np.ndarray,
) -> np.ndarray:
    """Transfer the median donor network change onto each query station lag."""
    if lag_hours not in features.lag_hours:
        raise ValueError(f"Requested lag is unavailable: {lag_hours}")
    fallback = other_station_mean_prediction(features, training_mean)
    prediction_columns = []
    for target in features.target_columns:
        lag = features.frame[f"{target}_lag{lag_hours}h"].to_numpy(float)
        change = features.frame[
            f"change_other__{target}__lag{lag_hours}h__median"
        ].to_numpy(float)
        prediction_columns.append(lag + change)
    prediction = np.column_stack(prediction_columns)
    return np.where(np.isfinite(prediction), prediction, fallback)


def feature_columns_for_groups(
    features: SpatialFusionFeatures,
    groups: Sequence[str],
) -> list[str]:
    """Return ordered feature columns for named, nonduplicated groups."""
    requested = tuple(groups)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("Feature groups must be nonempty and unique")
    missing = sorted(set(requested) - set(features.feature_groups))
    if missing:
        raise ValueError(f"Unknown feature groups: {missing}")
    return [column for group in requested for column in features.feature_groups[group]]


def select_per_target_by_validation(
    truth: np.ndarray,
    predictions: Mapping[str, np.ndarray],
    denominators: np.ndarray,
    candidate_order: Sequence[str],
) -> tuple[str, ...]:
    """Select one precomputed candidate per target using validation RMSE only."""
    actual = np.asarray(truth, dtype=float)
    scale = _target_fallback(denominators, actual.shape[1])
    if set(candidate_order) != set(predictions) or len(set(candidate_order)) != len(
        candidate_order
    ):
        raise ValueError("candidate_order must name every prediction exactly once")
    scores = []
    for name in candidate_order:
        prediction = np.asarray(predictions[name], dtype=float)
        if prediction.shape != actual.shape:
            raise ValueError("Every prediction must have the same shape as truth")
        scores.append(np.sqrt(np.mean((prediction - actual) ** 2, axis=0)) / scale)
    selected_indices = np.argmin(np.vstack(scores), axis=0)
    return tuple(candidate_order[index] for index in selected_indices)


def compose_per_target_predictions(
    selected_models: Sequence[str],
    predictions: Mapping[str, np.ndarray],
) -> np.ndarray:
    """Compose target columns from validation selected candidate models."""
    if not predictions:
        raise ValueError("Predictions must be nonempty")
    first = np.asarray(next(iter(predictions.values())), dtype=float)
    if first.ndim != 2 or len(selected_models) != first.shape[1]:
        raise ValueError("Selected models must contain one name per target")
    result = np.empty_like(first)
    for target_index, model in enumerate(selected_models):
        if model not in predictions:
            raise ValueError(f"Unknown selected model: {model}")
        prediction = np.asarray(predictions[model], dtype=float)
        if prediction.shape != first.shape:
            raise ValueError("Every prediction must have the same shape")
        result[:, target_index] = prediction[:, target_index]
    return result


def _nan_statistics(values: np.ndarray) -> dict[str, np.ndarray]:
    """Compute row statistics while retaining missing rows without warnings."""
    matrix = np.asarray(values, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return {
            "mean": np.nanmean(matrix, axis=1),
            "median": np.nanmedian(matrix, axis=1),
            "std": np.nanstd(matrix, axis=1),
            "min": np.nanmin(matrix, axis=1),
            "max": np.nanmax(matrix, axis=1),
        }


def _target_fallback(values: np.ndarray, target_count: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (target_count,) or not np.all(np.isfinite(array)):
        raise ValueError("Expected one finite value per target")
    return array
