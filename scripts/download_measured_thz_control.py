from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "dpw4svmdr8"
DATASET_VERSION = 1
DATASET_DOI = "10.17632/dpw4svmdr8.1"
DATASET_PAGE = f"https://data.mendeley.com/datasets/{DATASET_ID}/{DATASET_VERSION}"
PUBLIC_FILE_LIST = (
    f"https://data.mendeley.com/public-api/datasets/{DATASET_ID}/files"
    f"?folder_id=root&version={DATASET_VERSION}"
)
USER_AGENT = "THz-ISAC-reproducibility/1.0"


def main() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw" / "measured_thz_control"
    result_dir = PROJECT_ROOT / "results" / "tables"
    raw_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = result_dir / "measured_thz_control_acquisition_manifest.json"

    endpoint_attempts = [
        _probe(
            f"https://api.mendeley.com/datasets/{DATASET_ID}"
            f"?version={DATASET_VERSION}"
        ),
        _probe(
            f"https://api.data.mendeley.com/datasets/publics/{DATASET_ID}/files"
            f"?version={DATASET_VERSION}"
        ),
        _probe(PUBLIC_FILE_LIST),
    ]

    file_records = json.loads(_request_bytes(PUBLIC_FILE_LIST).decode("utf-8"))
    acquired = []
    for record in file_records:
        filename = str(record["filename"])
        expected_sha256 = str(record["content_details"]["sha256_hash"])
        download_url = str(record["content_details"]["download_url"])
        payload = _request_bytes(download_url)
        actual_sha256 = hashlib.sha256(payload).hexdigest()
        if actual_sha256 != expected_sha256:
            raise RuntimeError(
                f"SHA256 mismatch for {filename}: expected {expected_sha256}, "
                f"received {actual_sha256}."
            )
        output_path = raw_dir / filename
        output_path.write_bytes(payload)
        acquired.append(
            {
                "filename": filename,
                "file_id": str(record["id"]),
                "bytes": len(payload),
                "repository_sha256": expected_sha256,
                "local_sha256": actual_sha256,
                "hash_verified": True,
                "source_url": download_url,
                "local_path": str(output_path.relative_to(PROJECT_ROOT)),
            }
        )

    manifest = {
        "status": "success",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "dataset": {
            "id": DATASET_ID,
            "version": DATASET_VERSION,
            "doi": DATASET_DOI,
            "page": DATASET_PAGE,
            "title": (
                "Data for Terahertz spectroscopic study of liquid-liquid "
                "phase separation of protein solutions"
            ),
            "contributor": "Toshiaki Hattori",
            "licence": "CC BY 4.0",
            "published": "2024-11-14",
        },
        "endpoint_attempts": endpoint_attempts,
        "successful_file_listing_endpoint": PUBLIC_FILE_LIST,
        "file_count": len(acquired),
        "files": acquired,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Downloaded and hash verified {len(acquired)} measured THz files.")
    print(f"Manifest: {manifest_path}")


def _request_bytes(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.mendeley-public-dataset.1+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def _probe(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            response.read(256)
            return {
                "url": url,
                "http_status": int(response.status),
                "outcome": "reachable",
            }
    except HTTPError as error:
        return {
            "url": url,
            "http_status": int(error.code),
            "outcome": "http_error",
        }
    except (URLError, TimeoutError) as error:
        return {
            "url": url,
            "http_status": None,
            "outcome": "network_error",
            "error_type": type(error).__name__,
        }


if __name__ == "__main__":
    main()
