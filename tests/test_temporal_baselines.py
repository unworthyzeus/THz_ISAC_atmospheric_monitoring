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

from thz_isac.temporal_baselines import (  # noqa: E402
    build_exact_causal_lag_features,
    evenly_spaced_sample_indices,
)


def _source() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=5, freq="h"),
            "station": ["A"] * 5,
            "pollutant": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )


def test_exact_causal_lag_uses_only_the_requested_past_timestamp():
    source = _source()
    query = source.iloc[[1, 3]][["datetime", "station"]].reset_index(drop=True)

    result = build_exact_causal_lag_features(
        source,
        query,
        ["pollutant"],
        [1, 2],
    )

    np.testing.assert_allclose(result.features["pollutant_lag1h"], [10.0, 30.0])
    assert np.isnan(result.features.loc[0, "pollutant_lag2h"])
    assert result.features.loc[0, "pollutant_lag2h_missing"] == 1.0
    assert result.features.loc[1, "pollutant_lag2h"] == 20.0
    for lag in (1, 2):
        matched = result.source_timestamps[f"source_datetime_lag{lag}h"].notna()
        delta = query.loc[matched, "datetime"].reset_index(drop=True) - pd.to_datetime(
            result.source_timestamps.loc[matched, f"source_datetime_lag{lag}h"]
        ).reset_index(drop=True)
        assert (delta == pd.Timedelta(hours=lag)).all()


def test_current_and_future_value_changes_cannot_change_a_past_lag():
    source = _source()
    query = source.iloc[[2]][["datetime", "station"]].reset_index(drop=True)
    before = build_exact_causal_lag_features(source, query, ["pollutant"], [1])

    changed = source.copy()
    changed.loc[changed["datetime"] >= query.loc[0, "datetime"], "pollutant"] = 9999.0
    after = build_exact_causal_lag_features(changed, query, ["pollutant"], [1])

    pd.testing.assert_frame_equal(before.features, after.features)
    assert before.features.loc[0, "pollutant_lag1h"] == 20.0


def test_causal_lag_builder_rejects_nonpositive_lags_and_duplicate_source_keys():
    source = _source()
    query = source.iloc[[2]][["datetime", "station"]]
    with pytest.raises(ValueError, match="unique positive"):
        build_exact_causal_lag_features(source, query, ["pollutant"], [0])

    duplicated = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="must be unique"):
        build_exact_causal_lag_features(duplicated, query, ["pollutant"], [1])


def test_evenly_spaced_indices_preserve_the_physical_benchmark_rule():
    np.testing.assert_array_equal(evenly_spaced_sample_indices(10, 4), [0, 3, 6, 9])
    with pytest.raises(ValueError, match="between one and n_rows"):
        evenly_spaced_sample_indices(3, 4)
