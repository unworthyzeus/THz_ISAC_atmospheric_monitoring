"""Strictly causal feature construction for the v2 ground sensor forecast."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


SELF_LAGS_HOURS = (1, 2, 3, 4, 6, 12, 24, 48, 72, 168, 336)
CROSS_TARGET_LAGS_HOURS = (1, 2, 24)
CITY_LAGS_HOURS = (1, 2, 3, 6, 24)
ROLLING_WINDOWS_HOURS = (3, 6, 12, 24, 48, 168)


@dataclass(frozen=True)
class HourlyHistory:
    """Hourly station cubes and past-only summary arrays."""

    times: pd.DatetimeIndex
    stations: tuple[str, ...]
    target_names: tuple[str, ...]
    weather_names: tuple[str, ...]
    targets: np.ndarray
    weather: np.ndarray
    cumulative_sum: np.ndarray
    cumulative_count: np.ndarray
    cumulative_square_sum: np.ndarray
    city_mean: np.ndarray
    city_median: np.ndarray

    @classmethod
    def from_frame(
        cls,
        frame: pd.DataFrame,
        target_names: Sequence[str],
        weather_names: Sequence[str],
        *,
        timestamp_column: str = "datetime",
        station_column: str = "station",
    ) -> "HourlyHistory":
        """Build a regular hourly cube from unique station observations."""
        targets = tuple(target_names)
        weather = tuple(weather_names)
        required = {timestamp_column, station_column, *targets, *weather}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"History source is missing columns: {missing}")
        timestamps = pd.to_datetime(frame[timestamp_column], errors="raise")
        keys = pd.DataFrame(
            {timestamp_column: timestamps, station_column: frame[station_column]}
        )
        if keys.duplicated([timestamp_column, station_column]).any():
            raise ValueError("History station and timestamp keys must be unique")
        times = pd.date_range(timestamps.min(), timestamps.max(), freq="h")
        stations = tuple(sorted(frame[station_column].astype(str).unique()))
        time_codes = times.get_indexer(timestamps)
        station_codes = pd.Index(stations).get_indexer(
            frame[station_column].astype(str)
        )
        target_cube = np.full(
            (len(times), len(stations), len(targets)), np.nan, dtype=np.float32
        )
        weather_cube = np.full(
            (len(times), len(stations), len(weather)), np.nan, dtype=np.float32
        )
        target_cube[time_codes, station_codes] = frame[list(targets)].to_numpy(
            np.float32
        )
        weather_cube[time_codes, station_codes] = frame[list(weather)].to_numpy(
            np.float32
        )
        finite = np.isfinite(target_cube)
        zero_filled = np.nan_to_num(target_cube, nan=0.0)
        leading_shape = (1, len(stations), len(targets))
        cumulative_sum = np.concatenate(
            [np.zeros(leading_shape), np.cumsum(zero_filled, axis=0)], axis=0
        )
        cumulative_count = np.concatenate(
            [np.zeros(leading_shape), np.cumsum(finite, axis=0)], axis=0
        )
        cumulative_square_sum = np.concatenate(
            [np.zeros(leading_shape), np.cumsum(zero_filled**2, axis=0)], axis=0
        )
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", category=RuntimeWarning)
            city_mean = np.nanmean(target_cube, axis=1)
            city_median = np.nanmedian(target_cube, axis=1)
        return cls(
            times=times,
            stations=stations,
            target_names=targets,
            weather_names=weather,
            targets=target_cube,
            weather=weather_cube,
            cumulative_sum=cumulative_sum,
            cumulative_count=cumulative_count,
            cumulative_square_sum=cumulative_square_sum,
            city_mean=city_mean,
            city_median=city_median,
        )

    def row_codes(
        self,
        frame: pd.DataFrame,
        *,
        timestamp_column: str = "datetime",
        station_column: str = "station",
    ) -> tuple[np.ndarray, np.ndarray]:
        """Map query rows to the regular history grid."""
        timestamps = pd.to_datetime(frame[timestamp_column], errors="raise")
        time_codes = self.times.get_indexer(timestamps)
        station_codes = pd.Index(self.stations).get_indexer(
            frame[station_column].astype(str)
        )
        if np.any(time_codes < 0) or np.any(station_codes < 0):
            raise ValueError(
                "Query contains a time or station outside the history grid"
            )
        return time_codes, station_codes

    @staticmethod
    def _past_lookup(array: np.ndarray, indices: np.ndarray) -> np.ndarray:
        output = np.full((len(indices), *array.shape[1:]), np.nan, dtype=np.float32)
        valid = (indices >= 0) & (indices < len(array))
        output[valid] = array[indices[valid]]
        return output

    def exact_target_lag(
        self, frame: pd.DataFrame, target_index: int, lag_hours: int
    ) -> np.ndarray:
        """Return one exact same-station target lag."""
        if lag_hours <= 0:
            raise ValueError("Target lag must be strictly positive")
        time_codes, station_codes = self.row_codes(frame)
        lagged = self._past_lookup(
            self.targets[:, :, target_index], time_codes - lag_hours
        )
        return lagged[np.arange(len(frame)), station_codes]

    def causal_base(
        self,
        frame: pd.DataFrame,
        target_index: int,
        station_fallback: np.ndarray,
    ) -> np.ndarray:
        """Use the previous station value, then previous city median, then train mean."""
        time_codes, station_codes = self.row_codes(frame)
        station_lag = self.exact_target_lag(frame, target_index, 1)
        city_lag = self._past_lookup(self.city_median[:, target_index], time_codes - 1)
        fallback = np.asarray(station_fallback, dtype=float)[station_codes]
        return np.where(
            np.isfinite(station_lag),
            station_lag,
            np.where(np.isfinite(city_lag), city_lag, fallback),
        )

    def feature_matrix(
        self,
        frame: pd.DataFrame,
        target_index: int,
        *,
        timestamp_column: str = "datetime",
    ) -> np.ndarray:
        """Build the frozen 189 feature information set using targets before t only."""
        time_codes, station_codes = self.row_codes(frame)
        timestamp = pd.to_datetime(frame[timestamp_column], errors="raise")
        blocks = []
        categorical = (
            (station_codes, len(self.stations)),
            (timestamp.dt.month.to_numpy() - 1, 12),
            (timestamp.dt.hour.to_numpy(), 24),
            (timestamp.dt.dayofweek.to_numpy(), 7),
        )
        for values, width in categorical:
            blocks.append(np.eye(width, dtype=np.float32)[values])

        current_weather = self.weather[time_codes, station_codes]
        past_weather = self._past_lookup(self.weather, time_codes - 1)[
            np.arange(len(frame)), station_codes
        ]
        blocks.extend([current_weather, past_weather, current_weather - past_weather])

        for lag in SELF_LAGS_HOURS:
            blocks.append(self.exact_target_lag(frame, target_index, lag)[:, None])
        for lag in CROSS_TARGET_LAGS_HOURS:
            lagged = self._past_lookup(self.targets, time_codes - lag)
            blocks.append(lagged[np.arange(len(frame)), station_codes])

        for window in ROLLING_WINDOWS_HOURS:
            lower = np.maximum(time_codes - window, 0)
            sums = (
                self.cumulative_sum[time_codes, station_codes, target_index]
                - self.cumulative_sum[lower, station_codes, target_index]
            )
            counts = (
                self.cumulative_count[time_codes, station_codes, target_index]
                - self.cumulative_count[lower, station_codes, target_index]
            )
            square_sums = (
                self.cumulative_square_sum[time_codes, station_codes, target_index]
                - self.cumulative_square_sum[lower, station_codes, target_index]
            )
            means = np.divide(
                sums,
                counts,
                out=np.full(len(frame), np.nan),
                where=counts > 0,
            )
            variances = (
                np.divide(
                    square_sums,
                    counts,
                    out=np.full(len(frame), np.nan),
                    where=counts > 0,
                )
                - means**2
            )
            blocks.extend(
                [
                    means[:, None].astype(np.float32),
                    np.sqrt(np.maximum(variances, 0.0))[:, None].astype(np.float32),
                    (counts / window)[:, None].astype(np.float32),
                ]
            )

        for lag in CITY_LAGS_HOURS:
            blocks.append(self._past_lookup(self.city_mean, time_codes - lag))
            blocks.append(self._past_lookup(self.city_median, time_codes - lag))
        blocks.append(
            self._past_lookup(self.targets[:, :, target_index], time_codes - 1)
        )
        return np.concatenate(blocks, axis=1)


def target_information_offsets_hours() -> tuple[int, ...]:
    """Return every target time offset used by the v2 features."""
    offsets = {
        *SELF_LAGS_HOURS,
        *CROSS_TARGET_LAGS_HOURS,
        *CITY_LAGS_HOURS,
        *range(1, max(ROLLING_WINDOWS_HOURS) + 1),
    }
    return tuple(sorted(offsets))
