"""Inventory a real Aura MLS radiance and retrieval data pair.

The script queries NASA Common Metadata Repository records for one UTC day and
performs a one byte ranged access check. It does not download the large Level 1
radiance granule. Aura MLS is a limb sounder, so these products are a real
submillimeter sensing control rather than surface pollution truth.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "results" / "tables" / "aura_mls_access_manifest.json"
CMR_COLLECTIONS = "https://cmr.earthdata.nasa.gov/search/collections.json"
CMR_GRANULES = "https://cmr.earthdata.nasa.gov/search/granules.json"
USER_AGENT = "THz-ISAC-atmospheric-monitoring/1.0"

PRODUCTS = (
    {
        "short_name": "ML1RADG",
        "version": "005",
        "role": "real calibrated Aura MLS GHz filter bank limb radiances",
    },
    {
        "short_name": "ML2CO",
        "version": "005",
        "role": "operational Aura MLS carbon monoxide profile retrieval",
    },
    {
        "short_name": "ML2O3",
        "version": "005",
        "role": "operational Aura MLS ozone profile retrieval",
    },
)


def parse_utc_day(value: str) -> date:
    """Parse one strict ISO calendar day as YYYY-MM-DD."""

    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"UTC day must use YYYY-MM-DD: {exc}") from exc
    if parsed.isoformat() != value:
        raise ValueError("UTC day must use YYYY-MM-DD")
    return parsed


def parse_args() -> argparse.Namespace:
    """Parse the requested sample day and output path."""

    parser = argparse.ArgumentParser(
        description="Check access to one paired Aura MLS Level 1 and Level 2 day."
    )
    parser.add_argument("--date", default="2013-03-01", help="UTC day as YYYY-MM-DD")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    try:
        parse_utc_day(args.date)
    except ValueError as exc:
        parser.error(str(exc))
    if args.timeout <= 0.0:
        parser.error("--timeout must be positive")
    return args


def read_json(url: str, timeout: float) -> dict[str, object]:
    """Read one public NASA CMR JSON response."""

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def cmr_url(endpoint: str, **parameters: str | int) -> str:
    """Build a stable CMR query URL."""

    parsed = urlsplit(endpoint)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("CMR endpoint must be an absolute HTTPS URL")
    if parsed.query or parsed.fragment:
        raise ValueError("CMR endpoint must not already contain a query or fragment")
    return f"{endpoint}?{urlencode(parameters)}"


def cmr_entries(payload: dict[str, object]) -> list[dict[str, object]]:
    """Validate and extract the entry list from a CMR feed response."""

    feed = payload.get("feed")
    if not isinstance(feed, dict):
        raise ValueError("CMR response does not contain a feed object")
    entries = feed.get("entry")
    if not isinstance(entries, list):
        raise ValueError("CMR response feed does not contain an entry list")
    if not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("CMR response entry list contains a nonobject value")
    return entries


def select_collection(
    short_name: str, version: str, timeout: float
) -> dict[str, object]:
    """Return the exact requested NASA collection metadata record."""

    payload = read_json(
        cmr_url(
            CMR_COLLECTIONS,
            short_name=short_name,
            version=version,
            page_size=20,
        ),
        timeout,
    )
    entries = cmr_entries(payload)
    matches = [
        entry
        for entry in entries
        if entry.get("short_name") == short_name
        and str(entry.get("version_id")) == version
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one {short_name} version {version} collection, found {len(matches)}"
        )
    if not isinstance(matches[0].get("id"), str) or not matches[0]["id"]:
        raise ValueError("CMR collection record does not contain a concept ID")
    return matches[0]


def day_interval(day: str) -> str:
    """Return the inclusive CMR temporal interval for one UTC day."""

    start_date = parse_utc_day(day)
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return f"{start.isoformat().replace('+00:00', 'Z')},{end.isoformat().replace('+00:00', 'Z')}"


def select_granule(
    collection_concept_id: str, day: str, timeout: float
) -> dict[str, object]:
    """Return the sole daily granule for a collection and UTC day."""

    payload = read_json(
        cmr_url(
            CMR_GRANULES,
            collection_concept_id=collection_concept_id,
            temporal=day_interval(day),
            page_size=20,
        ),
        timeout,
    )
    entries = cmr_entries(payload)
    if len(entries) != 1:
        raise ValueError(
            f"Expected one daily granule for {collection_concept_id}, found {len(entries)}"
        )
    return entries[0]


def data_url(granule: dict[str, object]) -> str:
    """Extract the first HTTPS data link from a CMR granule record."""

    links = granule.get("links")
    if not isinstance(links, list):
        raise ValueError("CMR granule does not contain a link list")
    for link in links:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        relation = link.get("rel")
        if not isinstance(href, str) or not isinstance(relation, str):
            continue
        parsed = urlsplit(href)
        if (
            relation.endswith("/data#")
            and parsed.scheme == "https"
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        ):
            return href
    raise ValueError("CMR granule does not expose an HTTPS data link")


def probe_indicates_download_access(probe: dict[str, object]) -> bool:
    """Return whether a ranged probe looks like file data rather than a login page."""

    ranged_get = probe.get("ranged_get")
    if not isinstance(ranged_get, dict):
        return False
    status = ranged_get.get("status")
    if status not in (200, 206) or ranged_get.get("bytes_read") != 1:
        return False
    content_type = str(ranged_get.get("content_type", "")).lower()
    if content_type in {"text/html", "application/xhtml+xml", "application/json"}:
        return False
    if status == 206:
        content_range = ranged_get.get("content_range")
        if not isinstance(content_range, str) or not content_range.startswith(
            "bytes 0-0/"
        ):
            return False
    return True


def access_probe(url: str, timeout: float) -> dict[str, object]:
    """Probe metadata and a single byte without storing the granule."""

    result: dict[str, object] = {}
    head_request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(head_request, timeout=timeout) as response:
            result["head"] = {
                "status": response.status,
                "content_length": response.headers.get("Content-Length"),
                "content_type": response.headers.get_content_type(),
                "final_url_host": response.url.split("/", 3)[2],
            }
    except (HTTPError, URLError) as exc:
        result["head"] = {
            "status": getattr(exc, "code", None),
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }

    get_request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
    )
    try:
        with urlopen(get_request, timeout=timeout) as response:
            first_byte = response.read(1)
            result["ranged_get"] = {
                "status": response.status,
                "bytes_read": len(first_byte),
                "content_range": response.headers.get("Content-Range"),
                "content_type": response.headers.get_content_type(),
                "final_url_host": urlsplit(response.url).hostname,
            }
    except (HTTPError, URLError) as exc:
        result["ranged_get"] = {
            "status": getattr(exc, "code", None),
            "exception_type": type(exc).__name__,
            "message": str(exc),
        }
    return result


def main() -> None:
    """Query, probe, and save the real radiance data access inventory."""

    args = parse_args()
    records = []
    failures = []
    for product in PRODUCTS:
        try:
            collection = select_collection(
                product["short_name"], product["version"], args.timeout
            )
            granule = select_granule(str(collection["id"]), args.date, args.timeout)
            url = data_url(granule)
            probe = access_probe(url, args.timeout)
            records.append(
                {
                    **product,
                    "collection_concept_id": collection["id"],
                    "collection_title": collection.get("dataset_id"),
                    "granule_title": granule.get("title"),
                    "producer_granule_id": granule.get("producer_granule_id"),
                    "reported_granule_size_mb": granule.get("granule_size"),
                    "time_start": granule.get("time_start"),
                    "time_end": granule.get("time_end"),
                    "data_url": url,
                    "access_probe": probe,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    **product,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    access_results = [
        probe_indicates_download_access(record["access_probe"]) for record in records
    ]
    if failures:
        status = "metadata_query_failed"
    elif access_results and all(access_results):
        status = "download_access_available"
    else:
        status = "blocked_by_earthdata_authentication"

    manifest = {
        "schema_version": 1,
        "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "sample_day_utc": args.date,
        "purpose": (
            "Identify a paired real submillimeter radiance and operational profile "
            "retrieval dataset for a future measured signal control."
        ),
        "records": records,
        "failures": failures,
        "interpretation": [
            "ML1RADG contains real calibrated Aura MLS limb radiances.",
            "ML2CO and ML2O3 are operational retrieval products derived from MLS observations, not independent ground truth.",
            "Aura MLS profiles represent the upper troposphere and higher atmosphere, not Beijing surface pollution.",
            "A successful access probe would authorize acquisition, not validate a retrieval model.",
        ],
        "limitations": [
            "NASA GES DISC granule downloads require a free Earthdata Login user account.",
            "No credentials are requested, stored, or printed by this script.",
            "The large Level 1 granule is intentionally not downloaded by this access check.",
            "Effective Level 1 use requires the MLS file description, calibration, quality flags, and instrument specific channel mapping.",
        ],
        "next_step": (
            "After the user supplies an authorized Earthdata access mechanism, "
            "download a bounded day, verify hashes and HDF5 structure, then define "
            "a profile and pressure matched chronological retrieval benchmark."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)

    print(f"Status: {status}")
    print(f"CMR products resolved: {len(records)}/{len(PRODUCTS)}")
    print(f"Metadata failures: {len(failures)}")
    print(f"Manifest: {args.output.resolve()}")


if __name__ == "__main__":
    main()
