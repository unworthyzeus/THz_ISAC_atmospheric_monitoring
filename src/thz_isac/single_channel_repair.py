"""Leakage controls for contemporaneous single channel sensor repair.

This task is distinct from strict sensor network reconstruction. For a target
channel being repaired, its current query station value is removed while the
other current pollutant channels at that same station remain available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SingleChannelRepairFeatures:
    """Target specific current query station covariates and audit arrays."""

    frames: Mapping[str, pd.DataFrame]
    current_query_values: np.ndarray
    target_columns: tuple[str, ...]
    feature_columns_by_target: Mapping[str, tuple[str, ...]]


def build_single_channel_repair_features(
    query: pd.DataFrame,
    target_columns: Sequence[str],
) -> SingleChannelRepairFeatures:
    """Mask only the current channel being repaired for each target design."""
    targets = tuple(target_columns)
    if len(targets) < 2 or len(set(targets)) != len(targets):
        raise ValueError("At least two unique target columns are required")
    missing = sorted(set(targets).difference(query.columns))
    if missing:
        raise ValueError(f"Query is missing target columns: {missing}")

    observed = query[list(targets)].to_numpy(float)
    target_count = len(targets)
    current_query_values = np.broadcast_to(
        observed[:, None, :],
        (len(query), target_count, target_count),
    ).copy()
    target_indices = np.arange(target_count)
    current_query_values[:, target_indices, target_indices] = np.nan

    frames: dict[str, pd.DataFrame] = {}
    columns_by_target: dict[str, tuple[str, ...]] = {}
    for repaired_index, repaired_target in enumerate(targets):
        source_indices = [
            source_index
            for source_index in range(target_count)
            if source_index != repaired_index
        ]
        columns = tuple(
            f"query_current_other_channel__{targets[source_index]}"
            for source_index in source_indices
        )
        frames[repaired_target] = pd.DataFrame(
            current_query_values[:, repaired_index, source_indices],
            columns=columns,
            index=query.index,
        )
        columns_by_target[repaired_target] = columns

    result = SingleChannelRepairFeatures(
        frames=frames,
        current_query_values=current_query_values,
        target_columns=targets,
        feature_columns_by_target=columns_by_target,
    )
    assert_repaired_current_target_excluded(result)
    return result


def assert_repaired_current_target_excluded(
    features: SingleChannelRepairFeatures,
) -> None:
    """Raise if any target design retains its own current query value."""
    target_count = len(features.target_columns)
    expected_shape = (
        len(next(iter(features.frames.values()))),
        target_count,
        target_count,
    )
    if features.current_query_values.shape != expected_shape:
        raise AssertionError("Single channel repair audit array has the wrong shape")
    diagonal = features.current_query_values[
        :, np.arange(target_count), np.arange(target_count)
    ]
    if not np.isnan(diagonal).all():
        raise AssertionError("A repaired current query target remains available")

    for target_index, target in enumerate(features.target_columns):
        frame = features.frames[target]
        forbidden = f"query_current_other_channel__{target}"
        if forbidden in frame.columns:
            raise AssertionError("A repaired target is present in its feature frame")
        expected_columns = {
            f"query_current_other_channel__{source}"
            for source_index, source in enumerate(features.target_columns)
            if source_index != target_index
        }
        if set(frame.columns) != expected_columns:
            raise AssertionError("Single channel covariates do not match the contract")


def repair_frame_for_target(
    features: SingleChannelRepairFeatures,
    repaired_target: str,
) -> pd.DataFrame:
    """Return the five permitted current query channels for one repair target."""
    if repaired_target not in features.frames:
        raise ValueError(f"Unknown repaired target: {repaired_target}")
    return features.frames[repaired_target]
