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

from thz_isac.single_channel_repair import (  # noqa: E402
    assert_repaired_current_target_excluded,
    build_single_channel_repair_features,
    repair_frame_for_target,
)


TARGETS = ("CO", "O3", "SO2", "NO2", "PM2.5", "PM10")


def make_query() -> pd.DataFrame:
    return pd.DataFrame(
        {
            target: np.arange(4, dtype=float) + 10.0 * index
            for index, target in enumerate(TARGETS)
        }
    )


def test_masks_only_the_channel_being_repaired() -> None:
    query = make_query()
    features = build_single_channel_repair_features(query, TARGETS)

    assert_repaired_current_target_excluded(features)
    co_frame = repair_frame_for_target(features, "CO")
    assert "query_current_other_channel__CO" not in co_frame
    assert len(co_frame.columns) == len(TARGETS) - 1
    np.testing.assert_allclose(
        co_frame["query_current_other_channel__O3"],
        query["O3"],
    )


def test_repaired_target_sentinel_cannot_change_its_design_matrix() -> None:
    query = make_query()
    changed = query.copy()
    changed["NO2"] = 999_999.0

    original_features = build_single_channel_repair_features(query, TARGETS)
    changed_features = build_single_channel_repair_features(changed, TARGETS)
    pd.testing.assert_frame_equal(
        repair_frame_for_target(original_features, "NO2"),
        repair_frame_for_target(changed_features, "NO2"),
    )
    assert not repair_frame_for_target(original_features, "CO").equals(
        repair_frame_for_target(changed_features, "CO")
    )


def test_rejects_missing_duplicate_and_unknown_targets() -> None:
    query = make_query()
    with pytest.raises(ValueError, match="unique"):
        build_single_channel_repair_features(query, ("CO", "CO"))
    with pytest.raises(ValueError, match="missing"):
        build_single_channel_repair_features(query, (*TARGETS, "NH3"))

    features = build_single_channel_repair_features(query, TARGETS)
    with pytest.raises(ValueError, match="Unknown"):
        repair_frame_for_target(features, "NH3")
