"""Recover published spectroscopy without modifying historical manifests."""
from pathlib import Path
import contextlib
import hashlib
import json
import socket
import hapi
import pandas as pd
from download_external_data import table_to_frame

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = ROOT/'data/raw/payload_bounds'
    out = ROOT/'results/payload_bounds'
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    old = json.loads((ROOT/'results/task_completion/spectroscopy_acquisition.json').read_text())
    names = {'H2CO', 'CH3OH', 'CH3CN', 'CO', 'O3', 'SO2', 'NO2'}
    hapi.VARIABLES['GLOBAL_HOST'] = 'https://hitran.org'
    socket.setdefaulttimeout(60)
    with (raw/'hapi.log').open('a') as log, contextlib.redirect_stdout(log):
        hapi.db_begin(str(raw))
    frames, records = [], []
    for previous in old['records']:
        if previous['molecule'] not in names or previous['status'] != 'acquired':
            continue
        r = dict(previous)
        name, mid, iso = r['molecule'], r['molecule_id'], r['isotopologue_id']
        table = f'{name}_iso{iso}_0_3000GHz'
        try:
            with (raw/'hapi.log').open('a') as log, contextlib.redirect_stdout(log):
                if not (raw/(table+'.data')).exists():
                    hapi.fetch(table, mid, iso, 0., 3000/29.9792458)
                frame = table_to_frame(table, dict(symbol=name, molecule_id=mid,
                    isotopologue_id=iso, role='target'))
            digest = hashlib.sha256((raw/(table+'.data')).read_bytes()).hexdigest()
            r['reacquired_data_sha256'] = digest
            r['matches_previous'] = digest == previous['data_sha256']
            frame['isotopologue_mass_g_mol'] = r['molar_mass_g_mol']
            frame['natural_abundance'] = r['natural_abundance']
            frames.append(frame)
            r['status'] = 'acquired'
        except Exception as exc:
            r.update(status='failed', error=str(exc))
        records.append(r)
        (out/'spectroscopy_acquisition.json').write_text(json.dumps(dict(
            source='https://hitran.org', records=records,
            scope='Same acquired isotope subset as historical study; unavailable requests remain excluded'), indent=2)+'\n')
        print(name, iso, r['status'], r.get('matches_previous'), flush=True)
    if any(r['status'] != 'acquired' for r in records):
        raise RuntimeError('Spectroscopy acquisition incomplete')
    pd.concat(frames, ignore_index=True).to_csv(raw/'lines.csv', index=False)


if __name__ == '__main__':
    main()
