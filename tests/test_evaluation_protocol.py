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

from thz_isac.evaluation_protocol import (  # noqa: E402
    chronological_timestamp_split,
    leave_stations_out_split,
    validate_disjoint_split,
)


def _metadata() -> pd.DataFrame:
    times = pd.date_range("2020-01-01", periods=10, freq="h")
    return pd.DataFrame(
        {
            "datetime": np.repeat(times, 3),
            "station": np.tile(["A", "B", "C"], len(times)),
        }
    )


def test_chronological_split_keeps_timestamp_groups_disjoint():
    metadata = _metadata()
    split = chronological_timestamp_split(metadata, train_fraction=0.6, validation_fraction=0.2)
    validate_disjoint_split(split, len(metadata))

    train_times = set(metadata.iloc[split.train]["datetime"])
    validation_times = set(metadata.iloc[split.validation]["datetime"])
    test_times = set(metadata.iloc[split.test]["datetime"])
    assert train_times.isdisjoint(validation_times)
    assert train_times.isdisjoint(test_times)
    assert validation_times.isdisjoint(test_times)
    assert max(train_times) < min(validation_times) < min(test_times)


def test_station_split_holds_complete_stations_out():
    metadata = _metadata()
    split = leave_stations_out_split(metadata, validation_stations=["B"], test_stations=["C"])
    validate_disjoint_split(split, len(metadata))

    assert set(metadata.iloc[split.train]["station"]) == {"A"}
    assert set(metadata.iloc[split.validation]["station"]) == {"B"}
    assert set(metadata.iloc[split.test]["station"]) == {"C"}


def test_station_split_rejects_overlap():
    with pytest.raises(ValueError, match="disjoint"):
        leave_stations_out_split(_metadata(), validation_stations=["A"], test_stations=["A"])
