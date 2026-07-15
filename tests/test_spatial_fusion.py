from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from thz_isac.spatial_fusion import (  # noqa: E402
    assert_query_current_targets_excluded,
    build_spatial_fusion_features,
    compose_per_target_predictions,
    feature_columns_for_groups,
    lag_delta_transfer_prediction,
    other_station_mean_prediction,
    select_per_target_by_validation,
)


TARGETS = ("target_1", "target_2")
WEATHER = ("temperature", "wind")


def _source() -> pd.DataFrame:
    rows = []
    starts = {"A": 10.0, "B": 100.0, "C": 30.0}
    for hour, timestamp in enumerate(pd.date_range("2024-01-01", periods=4, freq="h")):
        for station, start in starts.items():
            value = start + hour
            rows.append(
                {
                    "datetime": timestamp,
                    "station": station,
                    "target_1": value,
                    "target_2": 2.0 * value,
                    "temperature": 5.0 + hour,
                    "wind": 1.0 + 0.1 * hour,
                }
            )
    return pd.DataFrame(rows)


def _query(source: pd.DataFrame) -> pd.DataFrame:
    return source.loc[
        (source["station"] == "B")
        & (source["datetime"] == pd.Timestamp("2024-01-01 03:00:00")),
        ["datetime", "station", *WEATHER],
    ].reset_index(drop=True)


def _features(source: pd.DataFrame):
    return build_spatial_fusion_features(
        source,
        _query(source),
        TARGETS,
        WEATHER,
        (1, 2),
    )


def test_query_station_current_targets_are_masked_before_every_aggregate():
    features = _features(_source())
    assert_query_current_targets_excluded(features)

    assert np.isnan(features.frame.loc[0, "current_other__target_1__B"])
    assert features.frame.loc[0, "current_other__target_1__A"] == 13.0
    assert features.frame.loc[0, "current_other__target_1__C"] == 33.0
    assert features.frame.loc[0, "current_other__target_1__mean"] == 23.0
    assert features.frame.loc[0, "current_other__target_1__donor_count"] == 2.0


def test_current_query_label_sentinel_cannot_change_any_feature():
    source = _source()
    before = _features(source)
    changed = source.copy()
    current_query = (changed["station"] == "B") & (
        changed["datetime"] == pd.Timestamp("2024-01-01 03:00:00")
    )
    changed.loc[current_query, list(TARGETS)] = 999_999.0
    after = _features(changed)

    pd.testing.assert_frame_equal(before.frame, after.frame)
    np.testing.assert_allclose(
        before.current_other_values,
        after.current_other_values,
        equal_nan=True,
    )


def test_exact_lag_and_network_change_transfer_use_only_allowed_information():
    features = _features(_source())
    mean_prediction = other_station_mean_prediction(features, np.array([0.0, 0.0]))
    delta_prediction = lag_delta_transfer_prediction(
        features,
        1,
        np.array([0.0, 0.0]),
    )

    np.testing.assert_allclose(mean_prediction, [[23.0, 46.0]])
    np.testing.assert_allclose(delta_prediction, [[103.0, 206.0]])
    source_time = pd.to_datetime(
        features.lag_source_timestamps.loc[0, "source_datetime_lag1h"]
    )
    assert source_time == pd.Timestamp("2024-01-01 02:00:00")


def test_validation_selection_is_per_target_and_composition_preserves_columns():
    truth = np.zeros((3, 2))
    predictions = {
        "first": np.array([[0.0, 4.0], [0.0, 4.0], [0.0, 4.0]]),
        "second": np.array([[3.0, 0.0], [3.0, 0.0], [3.0, 0.0]]),
    }
    selected = select_per_target_by_validation(
        truth,
        predictions,
        np.ones(2),
        ("first", "second"),
    )

    assert selected == ("first", "second")
    np.testing.assert_allclose(
        compose_per_target_predictions(selected, predictions),
        np.zeros((3, 2)),
    )


def test_feature_group_selection_and_key_validation_are_explicit():
    source = _source()
    features = _features(source)
    selected = feature_columns_for_groups(
        features,
        ("spatial_current_aggregate", "query_causal_lag"),
    )
    assert "current_other__target_1__mean" in selected
    assert "target_1_lag1h" in selected

    duplicated = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="must be unique"):
        _features(duplicated)
    with pytest.raises(ValueError, match="Unknown feature groups"):
        feature_columns_for_groups(features, ("does_not_exist",))
