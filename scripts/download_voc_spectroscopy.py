"""Acquire external HITRAN VOC lines and archive a reproducible inventory.

No line positions or strengths are invented. Zero returned lines are recorded
as missing band coverage, not filled with proxy signatures.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import sys
import time

import pandas as pd
import hapi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from download_external_data import table_to_frame

MOLECULES = [
    ('H2CO', 20, 'voc'), ('CH3OH', 39, 'voc'), ('CH3CN', 41, 'voc'),
    ('CH4', 6, 'methane_band_control'),
    ('CO', 5, 'interferent'), ('O3', 3, 'interferent'),
    ('SO2', 9, 'interferent'), ('NO2', 10, 'interferent'),
    ('H2O', 1, 'background'), ('O2', 7, 'background'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--max-frequency-ghz', type=int, choices=[1000,3000], default=1000)
    args = parser.parse_args()
    suffix = '' if args.max_frequency_ghz == 1000 else '_0_3000'
    raw = ROOT / ('data/raw/voc_hitran_20260922'+suffix)
    out = ROOT / ('data/processed/voc_hitran_20260922'+suffix)
    ledger = ROOT / 'results/voc_pm_capacity'
    for directory in (raw, out, ledger):
        directory.mkdir(parents=True, exist_ok=True)
    log_path = raw / 'hapi_download.log'
    records, frames = [], []
    start = time.perf_counter()
    # Extended line-center windows permit explicit wing sensitivity checks.
    hapi.VARIABLES['GLOBAL_HOST'] = 'https://hitran.org'
    with log_path.open('a', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        hapi.db_begin(str(raw))
    for symbol, molecule_id, role in MOLECULES:
        table = symbol + f'_main_0_{args.max_frequency_ghz}GHz'
        record = dict(molecule=symbol, molecule_id=molecule_id, isotopologue_id=1, role=role)
        try:
            with log_path.open('a', encoding='utf-8') as log, contextlib.redirect_stdout(log):
                if args.refresh or not (raw / (table + '.data')).exists():
                    hapi.fetch(table, molecule_id, 1, 0., args.max_frequency_ghz / 29.9792458)
                frame = table_to_frame(table, dict(symbol=symbol, molecule_id=molecule_id,
                                                  isotopologue_id=1, role=role))
            frames.append(frame)
            record.update(status='acquired' if len(frame) else 'no_lines_in_download_window',
                          lines=len(frame), lines_60_400ghz=int(frame.frequency_ghz.between(60,400).sum()))
            for suffix in ('.data', '.header'):
                path = raw / (table + suffix)
                if path.exists():
                    record[suffix[1:]+'_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception as exc:
            record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        records.append(record)
        print(symbol, record, flush=True)
    destination = out / f'lines_0_{args.max_frequency_ghz}GHz.csv'
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(destination, index=False, lineterminator='\n')
    manifest = dict(acquired_utc=datetime.now(timezone.utc).isoformat(),
                    source='https://hitran.org', molecule_metadata='https://hitran.org/docs/molec-meta/',
                    isotopologue_metadata='https://hitran.org/docs/iso-meta/',
                    hapi_version=importlib.metadata.version('hitran-api'),
                    download_line_center_window_ghz=[0.,args.max_frequency_ghz], analysis_window_ghz=[60.,400.],
                    release='HITRANonline response at acquisition time; raw hashes pin exact returned data',
                    records=records, wall_seconds=time.perf_counter()-start,
                    processed_file=str(destination.relative_to(ROOT)),
                    processed_sha256=hashlib.sha256(destination.read_bytes()).hexdigest() if destination.exists() else None)
    name = 'acquisition_manifest.json' if args.max_frequency_ghz==1000 else 'acquisition_manifest_3000ghz.json'
    (ledger/name).write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    if any(r['status']=='failed' for r in records):
        raise SystemExit('Some downloads failed; retained the acquisition ledger. Inspect before analysis.')


if __name__ == '__main__':
    main()
