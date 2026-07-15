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

from thz_isac.causal_forecasting_v2 import (  # noqa: E402
    HourlyHistory,
    target_information_offsets_hours,
)


TARGETS = ("target_a", "target_b")
WEATHER = ("weather",)


def _history_frame() -> pd.DataFrame:
    rows = []
    for hour in range(6):
        for station_index, station in enumerate(("A", "B")):
            rows.append(
                {
                    "datetime": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=hour),
                    "station": station,
                    "target_a": float(10 * hour + station_index),
                    "target_b": float(100 + hour + station_index),
                    "weather": float(hour - station_index),
                }
            )
    return pd.DataFrame(rows)


def test_all_target_information_offsets_are_strictly_past():
    offsets = target_information_offsets_hours()
    assert offsets[0] == 1
    assert all(offset > 0 for offset in offsets)


def test_current_and_future_targets_cannot_change_v2_features():
    frame = _history_frame()
    query_time = pd.Timestamp("2024-01-01 04:00:00")
    query = pd.DataFrame({"datetime": [query_time], "station": ["A"], "weather": [4.0]})
    before = HourlyHistory.from_frame(frame, TARGETS, WEATHER).feature_matrix(query, 0)

    changed = frame.copy()
    changed.loc[changed["datetime"] >= query_time, list(TARGETS)] = 99999.0
    after = HourlyHistory.from_frame(changed, TARGETS, WEATHER).feature_matrix(query, 0)

    np.testing.assert_allclose(before, after, equal_nan=True)


def test_rolling_summaries_exclude_the_query_hour():
    frame = _history_frame()
    query = pd.DataFrame(
        {
            "datetime": [pd.Timestamp("2024-01-01 04:00:00")],
            "station": ["A"],
            "weather": [4.0],
        }
    )
    history = HourlyHistory.from_frame(frame, TARGETS, WEATHER)
    features = history.feature_matrix(query, 0)

    station_one_hot = 2
    calendar_one_hot = 12 + 24 + 7
    weather_features = 3
    self_lags = 11
    cross_lags = 3 * len(TARGETS)
    first_rolling_mean = (
        station_one_hot + calendar_one_hot + weather_features + self_lags + cross_lags
    )
    assert features[0, first_rolling_mean] == pytest.approx(20.0)


def test_history_rejects_duplicate_station_timestamp_keys():
    frame = _history_frame()
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="must be unique"):
        HourlyHistory.from_frame(duplicated, TARGETS, WEATHER)


def test_exact_target_lag_rejects_current_time():
    frame = _history_frame()
    history = HourlyHistory.from_frame(frame, TARGETS, WEATHER)
    query = frame.iloc[[4]][["datetime", "station"]]
    with pytest.raises(ValueError, match="strictly positive"):
        history.exact_target_lag(query, 0, 0)
