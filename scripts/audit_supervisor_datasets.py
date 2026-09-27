"""Record the exact spectroscopy and weather subsets used in the presentation."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
paths = ['data/raw/payload_bounds/lines.csv',
         'results/receiver_design/voc_pm_extension/lines.csv']
physics = json.loads((ROOT / 'results/joint_receiver_revision/physics_manifest.json').read_text(encoding='utf-8'))
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
for name, digest in hashes.items():
    assert physics['inputs'][name] == digest, f'Physics input changed: {name}'
lines = pd.concat([pd.read_csv(ROOT / p) for p in paths], ignore_index=True)
order = ['H2CO', 'CH3OH', 'CH3CN', 'CH3Cl', 'HCOOH', 'CO', 'O3', 'SO2', 'NO2']
records = []
for molecule in order:
    subset = lines[lines.molecule == molecule]
    records.append(dict(molecule=molecule,
                        isotopologue_ids=sorted(map(int, subset.isotopologue_id.unique())),
                        acquired_lines=len(subset),
                        centres_220_330_ghz=int(subset.frequency_ghz.between(220, 330).sum())))
weather_path = 'results/task_completion/weather_selection.json'
weather = json.loads((ROOT / weather_path).read_text(encoding='utf-8'))
output = dict(
    research_snapshot='461a3ba',
    spectroscopy=dict(source='https://hitran.org', input_sha256=hashes,
                      acquired_window_ghz=[0, 3000],
                      acquired_line_count=len(lines),
                      isotope_table_count=sum(len(r['isotopologue_ids']) for r in records),
                      centre_count_220_330_ghz=int(lines.frequency_ghz.between(220, 330).sum()),
                      records=records,
                      scope='All acquired lines enter the gas profiles with unlimited wings. Counts of centres in 220–330 GHz are descriptive, not a line selection filter.'),
    weather=dict(station='CHM00054511', archive='Beijing 2026 year to date snapshot',
                 source='https://www.ncei.noaa.gov/pub/data/igra/data/data-y2d/CHM00054511-data-beg2026.txt.zip',
                 provenance_file=weather_path, **weather),
    current_data_boundary='Current five VOC response experiments use controlled concentration scenarios, HITRAN and modeled/IGRA weather. UCI Beijing labels belong to earlier branches. No paired atmospheric THz and concentration dataset validates current recall.',
)
destination = ROOT / 'results/presentation_source_audit/dataset_subsets.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(f'Audited {len(lines):,} spectral lines and {weather["soundings"]} retained soundings')
