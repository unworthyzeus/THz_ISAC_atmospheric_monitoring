"""Acquire public aerosol measurements and primary references for closure work."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/five_task_closure"
OUT = ROOT / "results/five_task_closure"
DOI = "doi:10.57745/DLJEFW"
BASE = "https://entrepot.recherche.data.gouv.fr"


def fetch(url, path):
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    if "text/html" in response.headers.get("Content-Type", "") and "recaptcha" in response.text[:10000].lower():
        raise ValueError("Public endpoint returned a browser-check interstitial, not the source document")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return dict(url=url, file=str(path.relative_to(ROOT)), bytes=len(response.content),
                sha256=hashlib.sha256(response.content).hexdigest(), status="acquired")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    url = BASE + "/api/datasets/:persistentId/?persistentId=" + DOI
    metadata_record = fetch(url, OUT / "calcite_dataset_metadata.json")
    metadata = json.loads((OUT / "calcite_dataset_metadata.json").read_text(encoding="utf-8"))
    version = metadata["data"]["latestVersion"]

    def download(entry):
        info = entry["dataFile"]
        # Stable ASCII local paths preserve the original name in the manifest.
        path = RAW / "calcite" / (str(info["id"]) + Path(info["filename"]).suffix)
        url = BASE + "/api/access/datafile/" + str(info["id"])
        if path.exists():
            content = path.read_bytes()
            record = dict(url=url, file=str(path.relative_to(ROOT)), bytes=len(content),
                          sha256=hashlib.sha256(content).hexdigest(), status="acquired", reused_download=True)
        else:
            record = fetch(url, path)
        checksum = info["checksum"]
        actual = hashlib.new(checksum["type"].lower(), path.read_bytes()).hexdigest()
        if actual != checksum["value"]:
            raise ValueError("Repository checksum mismatch: " + info["filename"])
        return {**record, "original_filename": info["filename"], "source_checksum": checksum,
                "source_checksum_verified": True}

    # All corrected outputs and README; representative raw files expose trace
    # metadata without inventing a mass label that is absent from the record.
    wanted = [entry for entry in version["files"] if entry["dataFile"]["filename"].endswith(".txt")
              or entry["dataFile"]["id"] in [758284, 758289, 758288]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(download, wanted))
    references = [
        ("taleb2023.html", "https://www.nature.com/articles/s41598-023-47586-8"),
        ("who2021.html", "https://www.who.int/news-room/questions-and-answers/item/who-global-air-quality-guidelines"),
        ("who_indoor_formaldehyde.html", "https://www.ncbi.nlm.nih.gov/books/NBK138711/"),
        ("vdi_vnax_specs.pdf", "https://vadiodes.com/wp-content/uploads/2012/01/VDI-956_VNA-X_Typical_Performance_2022.03.17.pdf"),
        ("itu_resolution178.pdf", "https://www.itu.int/dms_pub/itu-r/md/00/ca/cir/R00-CA-CIR-0251!!PDF-E.pdf"),
        ("gudz2025.pdf", "https://hal.science/hal-05294637v1/document"),
    ]
    for name, link in references:
        try:
            records.append(fetch(link, RAW / name))
        except (requests.RequestException, ValueError) as error:
            records.append(dict(url=link, status="unavailable", reason=str(error)))
    manifest = dict(dataset_doi=DOI, dataset_version=f"{version['versionNumber']}.{version['versionMinorNumber']}",
                    acquired_date="2026-09-23", metadata=metadata_record, records=records,
                    scope="Measured calcite transmission and source documents; no atmospheric VOC/PM calibration claim")
    (OUT / "public_acquisition.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(dict(acquired=sum(r["status"] == "acquired" for r in records),
                          bytes=sum(r.get("bytes", 0) for r in records), dataset_version=manifest["dataset_version"])))


if __name__ == "__main__":
    main()
