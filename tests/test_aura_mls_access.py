from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_aura_mls_access as aura  # noqa: E402


def test_cmr_url_encodes_collection_and_temporal_parameters():
    interval = "2013-03-01T00:00:00Z,2013-03-01T23:59:59.999999Z"
    url = aura.cmr_url(
        aura.CMR_GRANULES,
        collection_concept_id="C123-TEST",
        temporal=interval,
        page_size=20,
    )

    parsed = urlsplit(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == aura.CMR_GRANULES
    assert parse_qs(parsed.query) == {
        "collection_concept_id": ["C123-TEST"],
        "temporal": [interval],
        "page_size": ["20"],
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://cmr.earthdata.nasa.gov/search/granules.json",
        "granules.json",
        "https://cmr.earthdata.nasa.gov/search/granules.json?existing=true",
    ],
)
def test_cmr_url_rejects_unsafe_or_ambiguous_endpoints(endpoint: str):
    with pytest.raises(ValueError, match="CMR endpoint"):
        aura.cmr_url(endpoint, page_size=20)


def test_day_interval_is_strict_and_spans_exactly_one_utc_day():
    assert aura.day_interval("2013-03-01") == (
        "2013-03-01T00:00:00Z,2013-03-01T23:59:59.999999Z"
    )
    for invalid in ("20130301", "2013-02-29", "2013-03-01T00:00:00Z"):
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            aura.day_interval(invalid)


def test_select_collection_validates_exact_short_name_version_and_concept_id(
    monkeypatch: pytest.MonkeyPatch,
):
    seen: dict[str, object] = {}

    def fake_read_json(url: str, timeout: float) -> dict[str, object]:
        seen.update(url=url, timeout=timeout)
        return {
            "feed": {
                "entry": [
                    {"short_name": "ML1RADG", "version_id": "004", "id": "OLD"},
                    {
                        "short_name": "ML1RADG",
                        "version_id": "005",
                        "id": "C123-TEST",
                    },
                    {"short_name": "OTHER", "version_id": "005", "id": "OTHER"},
                ]
            }
        }

    monkeypatch.setattr(aura, "read_json", fake_read_json)
    selected = aura.select_collection("ML1RADG", "005", timeout=12.5)

    assert selected["id"] == "C123-TEST"
    assert seen["timeout"] == 12.5
    query = parse_qs(urlsplit(str(seen["url"])).query)
    assert query == {
        "short_name": ["ML1RADG"],
        "version": ["005"],
        "page_size": ["20"],
    }


def test_select_granule_uses_the_strict_day_interval_without_network(
    monkeypatch: pytest.MonkeyPatch,
):
    seen: dict[str, object] = {}
    granule = {"title": "one day", "links": []}

    def fake_read_json(url: str, timeout: float) -> dict[str, object]:
        seen.update(url=url, timeout=timeout)
        return {"feed": {"entry": [granule]}}

    monkeypatch.setattr(aura, "read_json", fake_read_json)
    assert aura.select_granule("C123-TEST", "2013-03-01", 9.0) is granule
    query = parse_qs(urlsplit(str(seen["url"])).query)
    assert query["collection_concept_id"] == ["C123-TEST"]
    assert query["temporal"] == [aura.day_interval("2013-03-01")]
    assert seen["timeout"] == 9.0


@pytest.mark.parametrize(
    "payload,error",
    [
        ({}, "feed object"),
        ({"feed": {}}, "entry list"),
        ({"feed": {"entry": ["not an object"]}}, "nonobject"),
    ],
)
def test_cmr_entries_rejects_malformed_metadata(payload, error: str):
    with pytest.raises(ValueError, match=error):
        aura.cmr_entries(payload)


def test_data_url_skips_browse_http_and_malformed_links():
    expected = "https://data.example.test/path/MLS-file.he5"
    granule = {
        "links": [
            "not an object",
            {
                "rel": "http://esipfed.org/ns/fedsearch/1.1/browse#",
                "href": "https://example.test/preview.jpg",
            },
            {
                "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                "href": "http://data.example.test/insecure.he5",
            },
            {
                "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                "href": expected,
            },
        ]
    }

    assert aura.data_url(granule) == expected


@pytest.mark.parametrize(
    "granule",
    [
        {},
        {"links": {}},
        {
            "links": [
                {
                    "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                    "href": "https://user:secret@example.test/file.he5",
                }
            ]
        },
    ],
)
def test_data_url_rejects_missing_malformed_or_credentialed_links(granule):
    with pytest.raises(ValueError, match="link|HTTPS data link"):
        aura.data_url(granule)


@pytest.mark.parametrize(
    "ranged_get,expected",
    [
        (
            {
                "status": 206,
                "bytes_read": 1,
                "content_range": "bytes 0-0/1234",
                "content_type": "application/x-hdf5",
            },
            True,
        ),
        (
            {
                "status": 200,
                "bytes_read": 1,
                "content_range": None,
                "content_type": "application/octet-stream",
            },
            True,
        ),
        (
            {
                "status": 200,
                "bytes_read": 1,
                "content_range": None,
                "content_type": "text/html",
            },
            False,
        ),
        (
            {
                "status": 206,
                "bytes_read": 1,
                "content_range": None,
                "content_type": "application/x-hdf5",
            },
            False,
        ),
    ],
)
def test_probe_validation_does_not_accept_login_html_or_invalid_ranges(
    ranged_get: dict[str, object], expected: bool
):
    assert aura.probe_indicates_download_access({"ranged_get": ranged_get}) is expected
