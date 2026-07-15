"""Causal temporal feature utilities for auxiliary air quality baselines.

These helpers are intentionally separate from the spectroscopy inversion code.
Pollutant lag features are valid only when the corresponding past measurements
are available at inference time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CausalLagFeatures:
    """Exact lag values and the source timestamp used for every lag."""

    features: pd.DataFrame
    source_timestamps: pd.DataFrame


def evenly_spaced_sample_indices(n_rows: int, sample_size: int) -> np.ndarray:
    """Return the deterministic index rule used by the physical benchmark."""
    if n_rows < 1:
        raise ValueError("n_rows must be positive")
    if sample_size < 1 or sample_size > n_rows:
        raise ValueError("sample_size must be between one and n_rows")
    return np.linspace(0, n_rows - 1, sample_size, dtype=int)


def build_exact_causal_lag_features(
    source: pd.DataFrame,
    query: pd.DataFrame,
    value_columns: Sequence[str],
    lag_hours: Iterable[int],
    *,
    timestamp_column: str = "datetime",
    group_column: str = "station",
) -> CausalLagFeatures:
    """Join exact past values without nearest time matching or future access.

    For a query at time ``t`` and lag ``h``, the only eligible source row is the
    same group at exactly ``t - h``. Missing exact matches stay missing and are
    accompanied by an explicit indicator. Source timestamps are returned so an
    experiment can audit the causality contract.
    """
    values = tuple(value_columns)
    lags = tuple(int(lag) for lag in lag_hours)
    if not values:
        raise ValueError("At least one value column is required")
    if not lags:
        raise ValueError("At least one lag is required")
    if len(set(lags)) != len(lags) or any(lag <= 0 for lag in lags):
        raise ValueError("Lag hours must be unique positive integers")

    required_source = {timestamp_column, group_column, *values}
    required_query = {timestamp_column, group_column}
    missing_source = sorted(required_source.difference(source.columns))
    missing_query = sorted(required_query.difference(query.columns))
    if missing_source:
        raise ValueError(f"Source is missing columns: {missing_source}")
    if missing_query:
        raise ValueError(f"Query is missing columns: {missing_query}")

    source_keys = source[[group_column, timestamp_column]].copy()
    source_keys[timestamp_column] = pd.to_datetime(
        source_keys[timestamp_column], errors="raise"
    )
    if source_keys.duplicated([group_column, timestamp_column]).any():
        raise ValueError("Source group and timestamp keys must be unique")

    query_keys = query[[group_column, timestamp_column]].copy()
    query_keys[timestamp_column] = pd.to_datetime(
        query_keys[timestamp_column], errors="raise"
    )
    query_keys["_query_order"] = np.arange(len(query_keys))

    feature_columns: dict[str, np.ndarray] = {}
    timestamp_columns: dict[str, np.ndarray] = {}
    for lag in lags:
        source_time_column = f"source_{timestamp_column}_lag{lag}h"
        lookup_time_column = f"_lookup_{timestamp_column}"
        lookup = source[[group_column, timestamp_column, *values]].copy()
        lookup[timestamp_column] = pd.to_datetime(
            lookup[timestamp_column], errors="raise"
        )
        lookup[source_time_column] = lookup[timestamp_column]
        lookup[lookup_time_column] = lookup[timestamp_column] + pd.Timedelta(hours=lag)
        lookup = lookup.drop(columns=timestamp_column)

        joined = query_keys.merge(
            lookup,
            left_on=[group_column, timestamp_column],
            right_on=[group_column, lookup_time_column],
            how="left",
            sort=False,
            validate="many_to_one",
        ).sort_values("_query_order")

        matched = joined[source_time_column].notna()
        if matched.any():
            source_times = pd.to_datetime(joined.loc[matched, source_time_column])
            query_times = pd.to_datetime(joined.loc[matched, timestamp_column])
            expected_delta = pd.Timedelta(hours=lag)
            if not (source_times < query_times).all():
                raise AssertionError("Causal lag join accessed a nonpast timestamp")
            if not ((query_times - source_times) == expected_delta).all():
                raise AssertionError("Causal lag join did not preserve the exact lag")

        timestamp_columns[source_time_column] = joined[source_time_column].to_numpy()
        for value in values:
            feature_name = f"{value}_lag{lag}h"
            feature_columns[feature_name] = joined[value].to_numpy()
            feature_columns[f"{feature_name}_missing"] = (
                joined[value].isna().astype(float).to_numpy()
            )

    return CausalLagFeatures(
        features=pd.DataFrame(feature_columns, index=query.index),
        source_timestamps=pd.DataFrame(timestamp_columns, index=query.index),
    )
