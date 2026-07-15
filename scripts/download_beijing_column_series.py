"""Download a preliminary Beijing satellite column retrieval series.

The inputs are official ESA Climate Change Initiative monthly Level 3 files.
The extracted values are satellite retrievals, not ground truth and not direct
station measurements. Each product is sampled independently at the grid centre
nearest to the declared Beijing reference point.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import h5py
import numpy as np
from scipy.io import netcdf_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "columns" / "monthly" / "2013"
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "columns" / "beijing_column_series_2013.csv"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "columns"
    / "beijing_column_series_2013_manifest.json"
)

REFERENCE_LATITUDE = 39.9
REFERENCE_LONGITUDE = 116.4
EARLIEST_MONTH = "2013-03"
LATEST_MONTH = "2013-12"

CO_CATALOGUE = "https://catalogue.ceda.ac.uk/uuid/6242532d87d442a3acf0171d35c02e56/"
NO2_CATALOGUE = "https://doi.org/10.21944/cci-no2-omi-l3"

CSV_FIELDS = (
    "month",
    "reference_latitude_deg_north",
    "reference_longitude_deg_east",
    "co_status",
    "co_grid_latitude_deg_north",
    "co_grid_longitude_deg_east",
    "co_total_column_day_molecules_cm2",
    "co_total_column_uncertainty_day_molecules_cm2",
    "co_flag_day",
    "co_flag_day_meaning",
    "no2_status",
    "no2_grid_latitude_deg_north",
    "no2_grid_longitude_deg_east",
    "no2_tropospheric_column_molec_cm2",
    "no2_total_uncertainty_molec_cm2",
    "no2_temporal_std_molec_cm2",
    "no2_qa_l3",
    "no2_superobservation_count",
    "no2_effective_observation_count",
    "no2_cloud_fraction",
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Download and extract March through December 2013 ESA CCI CO and "
            "NO2 monthly retrievals at the declared Beijing reference cell."
        )
    )
    parser.add_argument("--start-month", default=EARLIEST_MONTH)
    parser.add_argument("--end-month", default=LATEST_MONTH)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing raw files before parsing them.",
    )
    args = parser.parse_args()
    validate_month_range(args.start_month, args.end_month)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def validate_month_range(start_month: str, end_month: str) -> None:
    """Reject malformed months and requests beyond the declared study window."""

    try:
        start = datetime.strptime(start_month, "%Y-%m")
        end = datetime.strptime(end_month, "%Y-%m")
        earliest = datetime.strptime(EARLIEST_MONTH, "%Y-%m")
        latest = datetime.strptime(LATEST_MONTH, "%Y-%m")
    except ValueError as exc:
        raise SystemExit(f"Months must use YYYY-MM: {exc}") from exc
    if start > end:
        raise SystemExit("The start month must not follow the end month.")
    if start < earliest or end > latest:
        raise SystemExit(
            f"This preliminary downloader is restricted to {EARLIEST_MONTH} "
            f"through {LATEST_MONTH}."
        )


def iter_months(start_month: str, end_month: str) -> list[str]:
    """Return inclusive YYYY-MM labels for the requested range."""

    current = datetime.strptime(start_month, "%Y-%m")
    end = datetime.strptime(end_month, "%Y-%m")
    months = []
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months


def source_records(month: str) -> tuple[dict[str, str], dict[str, str]]:
    """Build the exact official product URLs and filenames for one month."""

    compact = month.replace("-", "")
    year = month[:4]
    co_filename = (
        "ESACCI-PREC-L3S-CO-IASI_MOPITT_MERGED_LATMOS-"
        f"180x360_1M-{compact}-fv1.0.nc"
    )
    no2_filename = (
        "ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-"
        f"0180x0360_1M-{compact}-fv1.0.nc"
    )
    return (
        {
            "product": "co",
            "product_id": f"esacci_merged_co_{compact}",
            "quantity": "total CO column, daytime retrieval",
            "resolution": "1 degree monthly",
            "catalogue": CO_CATALOGUE,
            "filename": co_filename,
            "url": (
                "https://dap.ceda.ac.uk/neodc/esacci/precursors/data/"
                f"MERGED_CO/v1.0/{year}/{co_filename}"
            ),
        },
        {
            "product": "no2",
            "product_id": f"esacci_omi_no2_1deg_{compact}",
            "quantity": "tropospheric NO2 vertical column retrieval",
            "resolution": "1 degree monthly",
            "catalogue": NO2_CATALOGUE,
            "filename": no2_filename,
            "url": (
                "https://d1qb6yzwaaq4he.cloudfront.net/airpollution/"
                f"no2col/cci-no2/omi/{year}/{no2_filename}"
            ),
        },
    )


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_file(
    source: dict[str, str], path: Path, timeout: float, overwrite: bool
) -> dict[str, object]:
    """Download one raw file atomically and return acquisition metadata."""

    if path.exists() and not overwrite:
        return {
            "downloaded": False,
            "http_status": None,
            "content_type": None,
            "reported_content_length": None,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = path.with_suffix(path.suffix + ".part")
    if partial_path.exists():
        partial_path.unlink()
    request = Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=timeout) as response, partial_path.open(
            "wb"
        ) as handle:
            while block := response.read(1024 * 1024):
                handle.write(block)
            metadata = {
                "downloaded": True,
                "http_status": response.status,
                "content_type": response.headers.get_content_type(),
                "reported_content_length": response.headers.get("Content-Length"),
            }
        partial_path.replace(path)
        return metadata
    except Exception:
        if partial_path.exists():
            partial_path.unlink()
        raise


def nearest_index(coordinates: np.ndarray, target: float) -> int:
    """Return the index of the finite coordinate nearest to a target."""

    coordinates = np.asarray(coordinates, dtype=float)
    if coordinates.ndim != 1 or not np.isfinite(coordinates).any():
        raise ValueError("Expected a one dimensional finite coordinate array.")
    distances = np.where(np.isfinite(coordinates), np.abs(coordinates - target), np.inf)
    return int(np.argmin(distances))


def finite_or_none(value: object) -> float | int | None:
    """Convert a NumPy scalar to a JSON safe number or missing value."""

    scalar = np.asarray(value).reshape(()).item()
    if isinstance(scalar, (float, np.floating)):
        return float(scalar) if math.isfinite(float(scalar)) else None
    if isinstance(scalar, (int, np.integer)):
        return int(scalar)
    raise TypeError(f"Unsupported extracted scalar type: {type(scalar).__name__}")


def co_flag_meaning(flag: int | None) -> str | None:
    """Decode the documented daytime CO instrument flag."""

    return {
        0: "no_data",
        1: "MOPITT_only",
        2: "IASI_only",
        3: "IASI_and_MOPITT",
    }.get(flag)


def extract_co(path: Path) -> dict[str, object]:
    """Extract the nearest daytime CO retrieval and documented support fields."""

    with h5py.File(path, "r") as handle:
        latitude = np.asarray(handle["latitude"])
        longitude = np.asarray(handle["longitude"])
        latitude_index = nearest_index(latitude, REFERENCE_LATITUDE)
        longitude_index = nearest_index(longitude, REFERENCE_LONGITUDE)
        location = (0, latitude_index, longitude_index)
        value = finite_or_none(handle["co_total_column_day"][location])
        uncertainty = finite_or_none(
            handle["co_total_column_uncertainty_day"][location]
        )
        flag = finite_or_none(handle["flag_day"][location])
    return {
        "grid_latitude_deg_north": float(latitude[latitude_index]),
        "grid_longitude_deg_east": float(longitude[longitude_index]),
        "latitude_index": latitude_index,
        "longitude_index": longitude_index,
        "co_total_column_day_molecules_cm2": value,
        "co_total_column_uncertainty_day_molecules_cm2": uncertainty,
        "co_flag_day": flag,
        "co_flag_day_meaning": co_flag_meaning(flag),
        "source_variables": {
            "retrieval": "co_total_column_day",
            "uncertainty": "co_total_column_uncertainty_day",
            "flag": "flag_day",
        },
    }


def extract_no2(path: Path) -> dict[str, object]:
    """Extract the nearest NO2 retrieval and documented quality fields."""

    with netcdf_file(path, "r", mmap=False) as handle:
        latitude = np.asarray(handle.variables["latitude"].data)
        longitude = np.asarray(handle.variables["longitude"].data)
        latitude_index = nearest_index(latitude, REFERENCE_LATITUDE)
        longitude_index = nearest_index(longitude, REFERENCE_LONGITUDE)
        location = (0, latitude_index, longitude_index)

        def value(variable_name: str) -> float | int | None:
            return finite_or_none(handle.variables[variable_name].data[location])

        extracted = {
            "no2_tropospheric_column_molec_cm2": value(
                "tropospheric_NO2_column_number_density"
            ),
            "no2_total_uncertainty_molec_cm2": value(
                "tropospheric_NO2_column_number_density_total_uncertainty"
            ),
            "no2_temporal_std_molec_cm2": value(
                "tropospheric_NO2_column_number_density_temporal_std"
            ),
            "no2_qa_l3": value("qa_L3"),
            "no2_superobservation_count": value("no_observations"),
            "no2_effective_observation_count": value(
                "tropospheric_NO2_column_number_density_count"
            ),
            "no2_cloud_fraction": value("cloud_fraction"),
        }
    return {
        "grid_latitude_deg_north": float(latitude[latitude_index]),
        "grid_longitude_deg_east": float(longitude[longitude_index]),
        "latitude_index": latitude_index,
        "longitude_index": longitude_index,
        **extracted,
        "source_variables": {
            "retrieval": "tropospheric_NO2_column_number_density",
            "uncertainty": (
                "tropospheric_NO2_column_number_density_total_uncertainty"
            ),
            "temporal_std": (
                "tropospheric_NO2_column_number_density_temporal_std"
            ),
            "qa": "qa_L3",
            "superobservation_count": "no_observations",
            "effective_observation_count": (
                "tropospheric_NO2_column_number_density_count"
            ),
            "cloud_fraction": "cloud_fraction",
        },
    }


def empty_csv_row(month: str) -> dict[str, object]:
    """Create one output row that can retain independent product failures."""

    return {
        key: "" for key in CSV_FIELDS
    } | {
        "month": month,
        "reference_latitude_deg_north": REFERENCE_LATITUDE,
        "reference_longitude_deg_east": REFERENCE_LONGITUDE,
        "co_status": "not_attempted",
        "no2_status": "not_attempted",
    }


def write_csv(rows: list[dict[str, object]]) -> None:
    """Write the processed retrieval series with a stable column order."""

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(manifest: dict[str, object]) -> None:
    """Persist the acquisition manifest after each attempted product."""

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)


def extraction_to_csv(
    row: dict[str, object], product: str, extraction: dict[str, object]
) -> None:
    """Copy one product extraction into its processed CSV fields."""

    if product == "co":
        row.update(
            {
                "co_status": "retrieved",
                "co_grid_latitude_deg_north": extraction[
                    "grid_latitude_deg_north"
                ],
                "co_grid_longitude_deg_east": extraction[
                    "grid_longitude_deg_east"
                ],
                "co_total_column_day_molecules_cm2": extraction[
                    "co_total_column_day_molecules_cm2"
                ],
                "co_total_column_uncertainty_day_molecules_cm2": extraction[
                    "co_total_column_uncertainty_day_molecules_cm2"
                ],
                "co_flag_day": extraction["co_flag_day"],
                "co_flag_day_meaning": extraction["co_flag_day_meaning"],
            }
        )
    elif product == "no2":
        row.update(
            {
                "no2_status": "retrieved",
                "no2_grid_latitude_deg_north": extraction[
                    "grid_latitude_deg_north"
                ],
                "no2_grid_longitude_deg_east": extraction[
                    "grid_longitude_deg_east"
                ],
                "no2_tropospheric_column_molec_cm2": extraction[
                    "no2_tropospheric_column_molec_cm2"
                ],
                "no2_total_uncertainty_molec_cm2": extraction[
                    "no2_total_uncertainty_molec_cm2"
                ],
                "no2_temporal_std_molec_cm2": extraction[
                    "no2_temporal_std_molec_cm2"
                ],
                "no2_qa_l3": extraction["no2_qa_l3"],
                "no2_superobservation_count": extraction[
                    "no2_superobservation_count"
                ],
                "no2_effective_observation_count": extraction[
                    "no2_effective_observation_count"
                ],
                "no2_cloud_fraction": extraction["no2_cloud_fraction"],
            }
        )
    else:
        raise ValueError(f"Unsupported product: {product}")


def build_manifest(months: list[str]) -> dict[str, object]:
    """Create the fixed provenance and semantic declarations."""

    return {
        "schema_version": 1,
        "status": "in_progress",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": (
            "Preliminary real monthly Beijing column retrieval series for "
            "feasibility analysis."
        ),
        "period": {"start": months[0], "end": months[-1], "months": months},
        "declared_reference_point": {
            "latitude_deg_north": REFERENCE_LATITUDE,
            "longitude_deg_east": REFERENCE_LONGITUDE,
        },
        "sampling_rule": (
            "For each product and month, select the latitude and longitude grid "
            "centre independently nearest to the declared reference point."
        ),
        "retrieval_semantics": [
            "Values are Level 3 satellite retrievals and are never labeled as truth.",
            "The CO field is the daytime merged IASI and MOPITT total column.",
            "The NO2 field is the OMI tropospheric vertical column.",
            "Uncertainty, temporal variability, quality, counts, and cloud fields "
            "are retained without inventing replacement values.",
            "No satellite retrieval is treated as measured sub THz CSI.",
        ],
        "source_catalogues": {"co": CO_CATALOGUE, "no2": NO2_CATALOGUE},
        "outputs": {
            "csv": str(CSV_PATH.resolve()),
            "manifest": str(MANIFEST_PATH.resolve()),
            "raw_directory": str(RAW_DIR.resolve()),
        },
        "records": [],
        "failures": [],
    }


def main() -> None:
    """Download, extract, and inventory the requested monthly series."""

    args = parse_args()
    months = iter_months(args.start_month, args.end_month)
    rows = [empty_csv_row(month) for month in months]
    manifest = build_manifest(months)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    write_manifest(manifest)

    for month, row in zip(months, rows, strict=True):
        for source in source_records(month):
            path = RAW_DIR / source["filename"]
            try:
                http = download_file(source, path, args.timeout, args.overwrite)
                extraction = (
                    extract_co(path)
                    if source["product"] == "co"
                    else extract_no2(path)
                )
                extraction_to_csv(row, source["product"], extraction)
                manifest["records"].append(
                    {
                        "month": month,
                        **source,
                        "retrieval_status": "retrieved",
                        "local_path": str(path.resolve()),
                        "byte_size": path.stat().st_size,
                        "sha256": sha256_file(path),
                        "http": http,
                        "extraction": extraction,
                    }
                )
            except Exception as exc:
                row[f"{source['product']}_status"] = "failed"
                manifest["failures"].append(
                    {
                        "month": month,
                        "product": source["product"],
                        "product_id": source["product_id"],
                        "url": source["url"],
                        "local_path": str(path.resolve()),
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
            write_csv(rows)
            write_manifest(manifest)

    failures = len(manifest["failures"])
    successes = len(manifest["records"])
    expected = len(months) * 2
    if failures == 0 and successes == expected:
        manifest["status"] = "complete"
    elif successes:
        manifest["status"] = "partial"
    else:
        manifest["status"] = "failed"
    manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["summary"] = {
        "expected_product_months": expected,
        "successful_product_months": successes,
        "failed_product_months": failures,
        "csv_rows": len(rows),
        "raw_bytes": sum(record["byte_size"] for record in manifest["records"]),
    }
    write_csv(rows)
    write_manifest(manifest)

    print(f"Status: {manifest['status']}")
    print(f"CSV rows: {len(rows)}")
    print(f"Successful product months: {successes}/{expected}")
    print(f"Failures: {failures}")
    print(f"Raw bytes inventoried: {manifest['summary']['raw_bytes']}")
    print(f"CSV: {CSV_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
