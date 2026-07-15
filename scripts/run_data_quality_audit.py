from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_COLUMNS = [
    "CO_ug_m3",
    "O3_ug_m3",
    "SO2_ug_m3",
    "NO2_ug_m3",
    "PM2_5_ug_m3",
    "PM10_ug_m3",
]
EXPECTED_SOURCE_ROWS = 420_768
EXPECTED_STATIONS = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the processed UCI air quality records used by the study.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "air_quality" / "beijing_air_quality_clean.csv.gz",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise RuntimeError("Processed UCI data is missing. Run scripts/download_external_data.py first.")

    data = pd.read_csv(args.input, parse_dates=["datetime"])
    required = ["datetime", "station", "temperature_c", "pressure_hpa", "dew_point_c", *TARGET_COLUMNS]
    missing_columns = sorted(set(required) - set(data.columns))
    if missing_columns:
        raise RuntimeError(f"Missing required columns: {missing_columns}")

    key_duplicates = int(data.duplicated(["datetime", "station"]).sum())
    exact_duplicates = int(data.duplicated().sum())
    pm_order_violations = int((data["PM10_ug_m3"] < data["PM2_5_ug_m3"]).sum())
    dew_point_violations = int((data["dew_point_c"] > data["temperature_c"]).sum())
    nonpositive_targets = int((data[TARGET_COLUMNS] <= 0).sum().sum())
    expected_rows_per_station = EXPECTED_SOURCE_ROWS / EXPECTED_STATIONS

    summary_rows = [
        ("processed_rows", len(data), "count"),
        ("processed_columns", data.shape[1], "count"),
        ("source_complete_case_rate", len(data) / EXPECTED_SOURCE_ROWS, "fraction"),
        ("dropped_incomplete_rows", EXPECTED_SOURCE_ROWS - len(data), "count"),
        ("station_count", data["station"].nunique(), "count"),
        ("unique_timestamp_count", data["datetime"].nunique(), "count"),
        ("exact_duplicate_rows", exact_duplicates, "count"),
        ("duplicate_datetime_station_keys", key_duplicates, "count"),
        ("pm10_below_pm2_5_rows", pm_order_violations, "count"),
        ("pm10_below_pm2_5_rate", pm_order_violations / len(data), "fraction"),
        ("dew_point_above_temperature_rows", dew_point_violations, "count"),
        ("nonpositive_target_values", nonpositive_targets, "count"),
    ]
    summary = pd.DataFrame(summary_rows, columns=["check", "value", "unit"])

    station = data.groupby("station", as_index=False).size().rename(columns={"size": "complete_rows"})
    station["complete_case_rate"] = station["complete_rows"] / expected_rows_per_station
    station = station.sort_values("complete_case_rate")

    quantiles = data[TARGET_COLUMNS].quantile([0.05, 0.5, 0.95]).transpose()
    target_summary = data[TARGET_COLUMNS].agg(["count", "mean", "std", "min", "max"]).transpose()
    target_summary = target_summary.join(quantiles.rename(columns={0.05: "q05", 0.5: "median", 0.95: "q95"}))
    target_summary.index.name = "target"
    target_summary = target_summary.reset_index()

    correlations = data[TARGET_COLUMNS].corr()
    correlations.index.name = "target"

    tables_dir = PROJECT_ROOT / "results" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    summary_path = tables_dir / "data_quality_summary.csv"
    station_path = tables_dir / "data_quality_station_coverage.csv"
    targets_path = tables_dir / "data_quality_target_summary.csv"
    correlations_path = tables_dir / "data_quality_target_correlations.csv"
    manifest_path = tables_dir / "data_quality_manifest.json"

    summary.to_csv(summary_path, index=False)
    station.to_csv(station_path, index=False)
    target_summary.to_csv(targets_path, index=False)
    correlations.to_csv(correlations_path)
    manifest_path.write_text(
        json.dumps(
            {
                "source": "UCI Beijing Multi Site Air Quality dataset",
                "doi": "10.24432/C5RK5G",
                "input_path": str(args.input.relative_to(PROJECT_ROOT)),
                "input_sha256": sha256(args.input),
                "rows": int(len(data)),
                "columns": int(data.shape[1]),
                "time_start": data["datetime"].min().isoformat(),
                "time_end": data["datetime"].max().isoformat(),
                "stations": sorted(data["station"].unique().tolist()),
                "complete_case_filter": True,
                "target_columns": TARGET_COLUMNS,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Data quality audit complete.")
    print(f"summary: {summary_path}")
    print(f"station coverage: {station_path}")
    print(f"target summary: {targets_path}")
    print(f"target correlations: {correlations_path}")
    print(f"manifest: {manifest_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
