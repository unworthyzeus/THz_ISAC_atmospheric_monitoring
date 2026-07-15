"""Download and inventory a minimal real satellite column data pair.

The files are official ESA CCI monthly products for March 2013, which overlaps
the UCI Beijing record. This script only verifies acquisition and structure. It
does not join a satellite cell to station observations or treat retrievals as
ground truth.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

import h5py
from scipy.io import netcdf_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "columns" / "2013-03"
MANIFEST_PATH = (
    PROJECT_ROOT / "data" / "processed" / "column_smoke_data_manifest.json"
)

SOURCES = (
    {
        "id": "esacci_merged_co_201303",
        "quantity": "total CO column",
        "resolution": "1 degree monthly",
        "doi_or_catalogue": "https://catalogue.ceda.ac.uk/uuid/6242532d87d442a3acf0171d35c02e56/",
        "url": "https://dap.ceda.ac.uk/neodc/esacci/precursors/data/MERGED_CO/v1.0/2013/ESACCI-PREC-L3S-CO-IASI_MOPITT_MERGED_LATMOS-180x360_1M-201303-fv1.0.nc",
        "filename": "ESACCI-PREC-L3S-CO-IASI_MOPITT_MERGED-L3-201303-fv1.0.nc",
    },
    {
        "id": "esacci_omi_no2_coarse_201303",
        "quantity": "tropospheric NO2 column",
        "resolution": "2 by 2.5 degree monthly parser smoke grid",
        "doi_or_catalogue": "https://doi.org/10.21944/cci-no2-omi-l3",
        "url": "https://d1qb6yzwaaq4he.cloudfront.net/airpollution/no2col/cci-no2/omi/2013/ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-0091x0144_1M-201303-fv1.0.nc",
        "filename": "ESACCI-PREC-L3C-NO2-OMI-0091x0144-201303-fv1.0.nc",
    },
    {
        "id": "esacci_omi_no2_1deg_201303",
        "quantity": "tropospheric NO2 column",
        "resolution": "1 degree monthly science grid",
        "doi_or_catalogue": "https://doi.org/10.21944/cci-no2-omi-l3",
        "url": "https://d1qb6yzwaaq4he.cloudfront.net/airpollution/no2col/cci-no2/omi/2013/ESACCI-PREC-L3C-NO2-AURA_OMI_KNMI-0180x0360_1M-201303-fv1.0.nc",
        "filename": "ESACCI-PREC-L3C-NO2-OMI-0180x0360-201303-fv1.0.nc",
    },
)


def sha256_file(path: Path) -> str:
    """Return the SHA256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(source: dict[str, str], path: Path) -> dict[str, object]:
    """Download one source if absent and return HTTP metadata."""

    if path.exists():
        return {"downloaded": False, "http_status": None, "content_type": None}
    request = Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=180) as response, path.open("wb") as handle:
        while block := response.read(1024 * 1024):
            handle.write(block)
        return {
            "downloaded": True,
            "http_status": response.status,
            "content_type": response.headers.get_content_type(),
            "reported_content_length": response.headers.get("Content-Length"),
        }


def json_value(value):
    """Convert a NetCDF attribute to a compact JSON compatible value."""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list):
        return [json_value(item) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def inspect_hdf5(path: Path) -> dict[str, object]:
    """Inventory a NetCDF4 or HDF5 file through h5py."""

    variables: list[dict[str, object]] = []
    with h5py.File(path, "r") as handle:
        global_attributes = {
            key: json_value(value) for key, value in handle.attrs.items()
        }

        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                attributes = {
                    key: json_value(value) for key, value in obj.attrs.items()
                }
                variables.append(
                    {
                        "name": name,
                        "shape": list(obj.shape),
                        "dtype": str(obj.dtype),
                        "units": attributes.get("units"),
                        "long_name": attributes.get("long_name")
                        or attributes.get("standard_name"),
                        "fill_value": attributes.get("_FillValue"),
                        "scale_factor": attributes.get("scale_factor"),
                        "add_offset": attributes.get("add_offset"),
                    }
                )

        handle.visititems(visitor)
    return {
        "container": "HDF5 or NetCDF4",
        "global_attributes": global_attributes,
        "variables": variables,
    }


def inspect_classic_netcdf(path: Path) -> dict[str, object]:
    """Inventory a classic NetCDF file through SciPy."""

    with netcdf_file(path, "r", mmap=False) as handle:
        global_attributes = {
            key: json_value(value) for key, value in handle._attributes.items()
        }
        variables = []
        for name, variable in handle.variables.items():
            attributes = {
                key: json_value(value)
                for key, value in variable._attributes.items()
            }
            variables.append(
                {
                    "name": name,
                    "shape": list(variable.shape),
                    "dtype": str(variable.data.dtype),
                    "dimensions": list(variable.dimensions),
                    "units": attributes.get("units"),
                    "long_name": attributes.get("long_name")
                    or attributes.get("standard_name"),
                    "fill_value": attributes.get("_FillValue")
                    or attributes.get("missing_value"),
                    "scale_factor": attributes.get("scale_factor"),
                    "add_offset": attributes.get("add_offset"),
                }
            )
    return {
        "container": "classic NetCDF",
        "global_attributes": global_attributes,
        "variables": variables,
    }


def inspect_file(path: Path) -> dict[str, object]:
    """Detect and inventory a supported scientific data container."""

    with path.open("rb") as handle:
        magic = handle.read(8)
    if magic == b"\x89HDF\r\n\x1a\n":
        inventory = inspect_hdf5(path)
    elif magic.startswith(b"CDF"):
        inventory = inspect_classic_netcdf(path)
    else:
        raise ValueError(f"Unsupported data container magic: {magic!r}")
    inventory["magic_hex"] = magic.hex()
    return inventory


def main() -> None:
    """Download both files and write an acquisition inventory."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = []
    failures = []
    for source in SOURCES:
        path = OUTPUT_DIR / source["filename"]
        try:
            http = download(source, path)
            inventory = inspect_file(path)
            records.append(
                {
                    **source,
                    "local_path": str(path.resolve()),
                    "byte_size": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "http": http,
                    "inventory": inventory,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "id": source["id"],
                    "url": source["url"],
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    manifest = {
        "status": "parser smoke test only",
        "month": "2013-03",
        "beijing_overlap": True,
        "records": records,
        "failures": failures,
        "limitations": [
            "The NO2 file is intentionally coarse and is not the science grid.",
            "No satellite cell is joined to an individual UCI station.",
            "Satellite products are retrievals with uncertainty and prior dependence.",
            "No measured sub THz CSI is present.",
        ],
        "next_steps": [
            "Confirm coordinate orientation, missing values, units, and uncertainty fields.",
            "Download the matching 1 degree NO2 file for the science experiment.",
            "Extract a declared Beijing cell or regional mean with quality filtering.",
            "Implement a column normalized layered forward model.",
        ],
    }
    with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Records acquired: {len(records)}")
    print(f"Failures: {len(failures)}")
    for record in records:
        print(
            record["id"],
            record["byte_size"],
            record["sha256"],
            len(record["inventory"]["variables"]),
        )
    for failure in failures:
        print("FAILED", failure)
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
