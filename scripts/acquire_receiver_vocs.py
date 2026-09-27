"""Acquire an expanded organic gas inventory without altering prior snapshots."""
from pathlib import Path
from datetime import datetime, timezone
import contextlib
import hashlib
import json
import socket
import pandas as pd
import hapi
from download_external_data import table_to_frame

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design/voc_pm_extension'
RAW = ROOT/'data/raw/receiver_voc_extension'
CANDIDATES = [('CH3Cl', 24), ('HCOOH', 32), ('CH3Br', 40), ('C2H4', 38),
              ('CH3F', 51), ('CH3I', 54)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    socket.setdefaulttimeout(60)
    hapi.VARIABLES['GLOBAL_HOST'] = 'https://hitran.org'
    frames, records = [], []
    with (RAW/'acquisition.log').open('a', encoding='utf-8') as log, contextlib.redirect_stdout(log):
        hapi.db_begin(str(RAW))
    for name, mid in CANDIDATES:
        isotopes = sorted(i for m, i in hapi.ISO if m == mid)
        for iso in isotopes:
            record = dict(molecule=name, molecule_id=mid, isotopologue_id=iso)
            table = f'{name}_{iso}_0_3000GHz'
            try:
                with (RAW/'acquisition.log').open('a', encoding='utf-8') as log, contextlib.redirect_stdout(log):
                    if not (RAW/(table+'.data')).exists():
                        hapi.fetch(table, mid, iso, 0., 3000/29.9792458)
                    frame = table_to_frame(table, dict(symbol=name, molecule_id=mid, isotopologue_id=iso, role='candidate'))
                frames.append(frame)
                record.update(status='acquired' if len(frame) else 'no_lines_in_window',
                    lines=len(frame), lines_60_400=int(frame.frequency_ghz.between(60, 400).sum()),
                    lines_220_330=int(frame.frequency_ghz.between(220, 330).sum()),
                    isotope_abundance=float(hapi.abundance(mid, iso)),
                    isotope_mass_g_mol=float(hapi.molecularMass(mid, iso)),
                    raw_sha256={suffix: hashlib.sha256((RAW/(table+suffix)).read_bytes()).hexdigest()
                                for suffix in ['.data', '.header']})
            except Exception as exc:
                record.update(status='failed', error=f'{type(exc).__name__}: {exc}')
            records.append(record)
            print(record, flush=True)
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(OUT/'lines.csv', index=False, lineterminator='\n')
    manifest = dict(acquired_utc=datetime.now(timezone.utc).isoformat(), source='https://hitran.org',
        metadata='https://www.hitran.org/docs/molec-meta/', window_ghz=[0, 3000], records=records,
        scope='Organic gas candidates, not a regulatory VOC classification. No returned lines does not prove physical absence. No invented replacement spectra.',
        processed_sha256=hashlib.sha256((OUT/'lines.csv').read_bytes()).hexdigest() if frames else None)
    (OUT/'acquisition.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
