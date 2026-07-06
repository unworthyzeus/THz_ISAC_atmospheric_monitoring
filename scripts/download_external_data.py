from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from hapi import db_begin, fetch, getColumn


FREQUENCY_MIN_GHZ = 60.0
FREQUENCY_MAX_GHZ = 400.0
GHZ_PER_WAVENUMBER = 29.9792458
UCI_URL = "https://archive.ics.uci.edu/static/public/501/beijing+multi+site+air+quality+data.zip"

HITRAN_MOLECULES = [
    {"symbol": "O3", "molecule_id": 3, "isotopologue_id": 1, "role": "target"},
    {"symbol": "CO", "molecule_id": 5, "isotopologue_id": 1, "role": "target"},
    {"symbol": "SO2", "molecule_id": 9, "isotopologue_id": 1, "role": "target"},
    {"symbol": "NO2", "molecule_id": 10, "isotopologue_id": 1, "role": "target"},
    {"symbol": "H2O", "molecule_id": 1, "isotopologue_id": 1, "role": "background"},
    {"symbol": "O2", "molecule_id": 7, "isotopologue_id": 1, "role": "background"},
]


def main() -> None:
    raw_hitran_dir = PROJECT_ROOT / "data" / "raw" / "hitran"
    raw_air_dir = PROJECT_ROOT / "data" / "raw" / "air_quality"
    processed_hitran_dir = PROJECT_ROOT / "data" / "processed" / "hitran"
    processed_air_dir = PROJECT_ROOT / "data" / "processed" / "air_quality"
    for path in [raw_hitran_dir, raw_air_dir, processed_hitran_dir, processed_air_dir]:
        path.mkdir(parents=True, exist_ok=True)

    hitran_lines = download_hitran(raw_hitran_dir)
    hitran_path = processed_hitran_dir / "hitran_60_400GHz_lines.csv"
    hitran_lines.to_csv(hitran_path, index=False)

    air_quality = download_and_process_uci_air_quality(raw_air_dir)
    clean_path = processed_air_dir / "beijing_air_quality_clean.csv.gz"
    sample_path = processed_air_dir / "beijing_air_quality_model_sample.csv.gz"
    air_quality.to_csv(clean_path, index=False, compression="gzip")
    air_quality.sample(n=min(50_000, len(air_quality)), random_state=7).to_csv(
        sample_path,
        index=False,
        compression="gzip",
    )

    summary = {
        "hitran": {
            "frequency_min_ghz": FREQUENCY_MIN_GHZ,
            "frequency_max_ghz": FREQUENCY_MAX_GHZ,
            "wavenumber_min_cm_1": FREQUENCY_MIN_GHZ / GHZ_PER_WAVENUMBER,
            "wavenumber_max_cm_1": FREQUENCY_MAX_GHZ / GHZ_PER_WAVENUMBER,
            "molecules": HITRAN_MOLECULES,
            "line_count": int(len(hitran_lines)),
            "output": str(hitran_path),
        },
        "air_quality": {
            "source_url": UCI_URL,
            "clean_rows": int(len(air_quality)),
            "stations": sorted(air_quality["station"].dropna().unique().tolist()),
            "output": str(clean_path),
            "sample_output": str(sample_path),
        },
    }
    summary_path = PROJECT_ROOT / "data" / "processed" / "external_data_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("External data download complete.")
    print(f"HITRAN lines: {hitran_path}")
    print(f"Air quality clean data: {clean_path}")
    print(f"Air quality model sample: {sample_path}")
    print(f"Summary: {summary_path}")


def download_hitran(raw_hitran_dir: Path) -> pd.DataFrame:
    cwd = Path.cwd()
    os.chdir(raw_hitran_dir)
    try:
        db_begin(str(raw_hitran_dir))
        numin = FREQUENCY_MIN_GHZ / GHZ_PER_WAVENUMBER
        numax = FREQUENCY_MAX_GHZ / GHZ_PER_WAVENUMBER
        frames = []
        for molecule in HITRAN_MOLECULES:
            table = f"{molecule['symbol']}_main_60_400GHz"
            fetch(table, molecule["molecule_id"], molecule["isotopologue_id"], numin, numax)
            frames.append(table_to_frame(table, molecule))
        return pd.concat(frames, ignore_index=True)
    finally:
        os.chdir(cwd)


def table_to_frame(table: str, molecule: dict) -> pd.DataFrame:
    columns = {
        "nu": "wavenumber_cm_1",
        "sw": "line_intensity",
        "a": "einstein_a",
        "gamma_air": "gamma_air",
        "gamma_self": "gamma_self",
        "elower": "lower_state_energy",
        "n_air": "temperature_exponent",
        "delta_air": "air_pressure_shift",
    }
    data = {}
    for source_name, target_name in columns.items():
        data[target_name] = list(getColumn(table, source_name))
    frame = pd.DataFrame(data)
    frame["frequency_ghz"] = frame["wavenumber_cm_1"] * GHZ_PER_WAVENUMBER
    frame["molecule"] = molecule["symbol"]
    frame["molecule_id"] = molecule["molecule_id"]
    frame["isotopologue_id"] = molecule["isotopologue_id"]
    frame["role"] = molecule["role"]
    return frame[
        [
            "molecule",
            "molecule_id",
            "isotopologue_id",
            "role",
            "wavenumber_cm_1",
            "frequency_ghz",
            "line_intensity",
            "einstein_a",
            "gamma_air",
            "gamma_self",
            "lower_state_energy",
            "temperature_exponent",
            "air_pressure_shift",
        ]
    ]


def download_and_process_uci_air_quality(raw_air_dir: Path) -> pd.DataFrame:
    zip_path = raw_air_dir / "beijing_multi_site_air_quality_data.zip"
    if not zip_path.exists():
        req = Request(UCI_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=120) as response:
            zip_path.write_bytes(response.read())

    extract_dir = raw_air_dir / "beijing_multi_site_air_quality_data"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)

    for nested_zip in extract_dir.rglob("*.zip"):
        nested_dir = nested_zip.with_suffix("")
        nested_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(nested_zip) as archive:
            archive.extractall(nested_dir)

    csv_paths = sorted(extract_dir.rglob("PRSA_Data_*.csv"))
    if not csv_paths:
        raise RuntimeError(f"No PRSA CSV files found in {extract_dir}")

    frames = [pd.read_csv(path) for path in csv_paths]
    data = pd.concat(frames, ignore_index=True)
    data["datetime"] = pd.to_datetime(data[["year", "month", "day", "hour"]])

    required = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3", "TEMP", "PRES", "DEWP", "RAIN", "WSPM", "station"]
    keep = ["datetime", "year", "month", "day", "hour"] + required
    clean = data[keep].dropna(subset=required).copy()
    clean = clean.rename(
        columns={
            "PM2.5": "PM2_5_ug_m3",
            "PM10": "PM10_ug_m3",
            "SO2": "SO2_ug_m3",
            "NO2": "NO2_ug_m3",
            "CO": "CO_ug_m3",
            "O3": "O3_ug_m3",
            "TEMP": "temperature_c",
            "PRES": "pressure_hpa",
            "DEWP": "dew_point_c",
            "RAIN": "rain_mm",
            "WSPM": "wind_speed_m_s",
        }
    )
    return clean.sort_values(["datetime", "station"]).reset_index(drop=True)


if __name__ == "__main__":
    main()
