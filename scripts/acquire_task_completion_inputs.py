"""Acquire primary-source weather, recommendations and isotopic spectroscopy.

Existing main-isotope downloads are reused. Missing rare-isotope coverage is
recorded explicitly; the acquisition never substitutes invented transitions.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import contextlib
import hashlib
import json
import sys
import urllib.request
import zipfile
import pandas as pd
import hapi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from download_external_data import table_to_frame
from download_voc_spectroscopy import MOLECULES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources-only', action='store_true')
    args = parser.parse_args()
    raw = ROOT / 'data/raw/task_completion'
    out = ROOT / 'data/processed/task_completion'
    ledger = ROOT / 'results/task_completion'
    for folder in (raw, out, ledger):
        folder.mkdir(parents=True, exist_ok=True)
    sources = {
        'P676-13.pdf': 'https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf',
        'P835-7.pdf': 'https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.835-7-202408-I!!PDF-E.pdf',
        'igra-format.txt': 'https://www.ncei.noaa.gov/pub/data/igra/data/igra2-data-format.txt',
        'beijing-2026.zip': 'https://www.ncei.noaa.gov/pub/data/igra/data/data-y2d/CHM00054511-data-beg2026.txt.zip',
    }
    records = []
    for name, url in sources.items():
        path = raw / name
        record = dict(file=str(path.relative_to(ROOT)), url=url)
        try:
            if not path.exists():
                req = urllib.request.Request(url, headers={'User-Agent': 'THzResearch/1.0'})
                with urllib.request.urlopen(req, timeout=60) as response:
                    content = response.read()
                if name.endswith('.pdf') and not content.startswith(b'%PDF'):
                    raise ValueError('Response is not a PDF')
                path.write_bytes(content)
            record.update(status='acquired', sha256=digest(path), bytes=path.stat().st_size)
            if name.endswith('.zip'):
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    if len(names) != 1:
                        raise ValueError('Expected one station file')
                    (raw / 'beijing-2026.txt').write_bytes(archive.read(names[0]))
        except Exception as exc:
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        records.append(record)
        print(name, record['status'], flush=True)
    (ledger / 'source_acquisition.json').write_text(json.dumps(dict(
        acquired_utc=datetime.now(timezone.utc).isoformat(), records=records), indent=2)+'\n')
    if args.sources_only:
        return
    frames, inventory = [], []
    hapi.VARIABLES['GLOBAL_HOST'] = 'https://hitran.org'
    with (raw / 'hapi.log').open('a') as log, contextlib.redirect_stdout(log):
        hapi.db_begin(str(raw))
    for symbol, mid, role in MOLECULES:
        iso_ids = sorted(i for m, i in hapi.ISO if m == mid)
        for iso in iso_ids:
            table = f'{symbol}_iso{iso}_0_3000GHz'
            record = dict(molecule=symbol, molecule_id=mid, isotopologue_id=iso,
                          natural_abundance=hapi.abundance(mid, iso),
                          molar_mass_g_mol=hapi.molecularMass(mid, iso))
            try:
                if iso == 1:
                    existing = ROOT / 'data/raw/voc_hitran_20260922_0_3000' / f'{symbol}_main_0_3000GHz'
                    for ext in ('.header', '.data'):
                        destination = raw / (table + ext)
                        if not destination.exists():
                            destination.write_bytes(existing.with_suffix(ext).read_bytes())
                    with (raw / 'hapi.log').open('a') as log, contextlib.redirect_stdout(log):
                        hapi.storage2cache(table)
                with (raw / 'hapi.log').open('a') as log, contextlib.redirect_stdout(log):
                    if not (raw / (table + '.data')).exists():
                        hapi.fetch(table, mid, iso, 0., 3000 / 29.9792458)
                    frame = table_to_frame(table, dict(symbol=symbol, molecule_id=mid,
                                                       isotopologue_id=iso, role=role))
                frame['isotopologue_mass_g_mol'] = record['molar_mass_g_mol']
                frame['natural_abundance'] = record['natural_abundance']
                # Intensities already include terrestrial abundance; do not multiply again.
                frames.append(frame)
                record.update(status='acquired' if len(frame) else 'no_lines_in_window',
                              lines=len(frame), lines_60_400=int(frame.frequency_ghz.between(60,400).sum()),
                              data_sha256=digest(raw / (table+'.data')),
                              header_sha256=digest(raw / (table+'.header')))
            except Exception as exc:
                record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            inventory.append(record)
            print(symbol, iso, record['status'], record.get('lines'), flush=True)
    if frames:
        destination = out / 'all_isotopes_0_3000GHz.csv'
        pd.concat(frames, ignore_index=True).to_csv(destination, index=False, lineterminator='\n')
    else:
        raise RuntimeError('No spectroscopy acquired')
    (ledger / 'spectroscopy_acquisition.json').write_text(json.dumps(dict(
        acquired_utc=datetime.now(timezone.utc).isoformat(), source='https://hitran.org',
        intensity_abundance_policy='HITRAN natural abundances already embedded in line intensities',
        analysis_window_ghz=[60,400], catalog_center_window_ghz=[0,3000],
        processed_file=str(destination.relative_to(ROOT)), processed_sha256=digest(destination),
        records=inventory), indent=2)+'\n')
    if any(r['status']=='failed' for r in inventory):
        raise SystemExit('Acquisition incomplete; inspect retained manifest')


if __name__ == '__main__':
    main()
