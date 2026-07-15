"""Leakage resistant data splits for air quality experiments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SplitIndices:
    train: np.ndarray
    validation: np.ndarray
    test: np.ndarray
    train_end: pd.Timestamp
    validation_end: pd.Timestamp


def chronological_timestamp_split(
    metadata: pd.DataFrame,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
    timestamp_column: str = "datetime",
) -> SplitIndices:
    """Split complete timestamp groups into train, validation, and test periods."""
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between zero and one")
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between zero and one")
    if train_fraction + validation_fraction >= 1.0:
        raise ValueError("train and validation fractions must leave a nonempty test period")
    if timestamp_column not in metadata:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    timestamps = pd.to_datetime(metadata[timestamp_column], errors="raise")
    unique_times = np.sort(timestamps.unique())
    if len(unique_times) < 3:
        raise ValueError("At least three unique timestamps are required")

    train_count = max(1, int(np.floor(len(unique_times) * train_fraction)))
    validation_count = max(1, int(np.floor(len(unique_times) * validation_fraction)))
    if train_count + validation_count >= len(unique_times):
        validation_count = len(unique_times) - train_count - 1
    if validation_count < 1:
        raise ValueError("The requested split leaves no validation timestamps")

    train_end = pd.Timestamp(unique_times[train_count - 1])
    validation_end = pd.Timestamp(unique_times[train_count + validation_count - 1])
    train = np.flatnonzero((timestamps <= train_end).to_numpy())
    validation = np.flatnonzero(((timestamps > train_end) & (timestamps <= validation_end)).to_numpy())
    test = np.flatnonzero((timestamps > validation_end).to_numpy())

    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("Chronological split produced an empty partition")
    return SplitIndices(
        train=train,
        validation=validation,
        test=test,
        train_end=train_end,
        validation_end=validation_end,
    )


def leave_stations_out_split(
    metadata: pd.DataFrame,
    validation_stations: list[str],
    test_stations: list[str],
    station_column: str = "station",
) -> SplitIndices:
    """Hold complete stations out for validation and test stress tests."""
    if station_column not in metadata:
        raise ValueError(f"Missing station column: {station_column}")
    validation_set = set(validation_stations)
    test_set = set(test_stations)
    if not validation_set or not test_set:
        raise ValueError("Validation and test station lists must be nonempty")
    if validation_set & test_set:
        raise ValueError("Validation and test stations must be disjoint")

    station = metadata[station_column].astype(str)
    known = set(station.unique())
    requested = validation_set | test_set
    missing = sorted(requested - known)
    if missing:
        raise ValueError(f"Unknown stations: {missing}")

    validation_mask = station.isin(validation_set).to_numpy()
    test_mask = station.isin(test_set).to_numpy()
    train_mask = ~(validation_mask | test_mask)
    train = np.flatnonzero(train_mask)
    validation = np.flatnonzero(validation_mask)
    test = np.flatnonzero(test_mask)
    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("Station split produced an empty partition")

    return SplitIndices(
        train=train,
        validation=validation,
        test=test,
        train_end=pd.NaT,
        validation_end=pd.NaT,
    )


def validate_disjoint_split(split: SplitIndices, n_rows: int) -> None:
    """Raise when partitions overlap, omit rows, or contain invalid indices."""
    arrays = [np.asarray(split.train), np.asarray(split.validation), np.asarray(split.test)]
    combined = np.concatenate(arrays)
    if len(combined) != n_rows:
        raise ValueError("Split does not assign every row exactly once")
    if len(np.unique(combined)) != n_rows:
        raise ValueError("Split partitions overlap")
    if combined.min(initial=0) < 0 or combined.max(initial=-1) >= n_rows:
        raise ValueError("Split contains an out of range index")
