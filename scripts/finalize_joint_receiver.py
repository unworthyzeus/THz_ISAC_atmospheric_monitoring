"""Pin the complete current revision and its external validation boundaries."""
from pathlib import Path
import json
import sys
import subprocess
import hashlib
import importlib.metadata
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/joint_receiver_revision'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if '--visual-reviewed' not in sys.argv:raise RuntimeError('Inspect all rendered pages and figures first')
    verification=json.loads((OUT/'verification.json').read_text())
    build=json.loads((OUT/'paper_build.json').read_text())
    suites=ET.parse(OUT/'pytest.xml').getroot().findall('testsuite')
    tests={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    if verification['status']!='passed' or tests['tests']==0 or tests['failures'] or tests['errors']:raise RuntimeError('Verification is incomplete')
    if sha(ROOT/build['output'])!=build['sha256']:raise RuntimeError('PDF changed after build')
    build['visual_review']='All rendered pages and all three percentage, limit and global PM figures inspected'
    (OUT/'paper_build.json').write_text(json.dumps(build,indent=2)+'\n',encoding='utf-8')
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='deliverable_manifest.json']
    files+=list((ROOT/'scripts').glob('*joint_receiver*.py'))
    files+=list((ROOT/'src/thz_isac').glob('*.py'))
    files+=[ROOT/p for p in ['.gitattributes','README.md','AGENTS.md','pytest.ini','I2R_proposal_THz_ISAC (1).pdf',
        'docs/43_original_proposal_remaining_tasks.md','docs/49_completion_audit_and_fixes.md',
        'docs/50_species_methods_and_percentage_guide.md','docs/51_joint_design_time_calibration_results.md',
        'paper/README.md','paper/main.tex','paper/current_study.tex','paper/joint_receiver_revision.tex',
        'paper/build/main.pdf',build['output'],'tests/test_joint_receiver_metrics.py']]
    # Pin inherited dependencies actually used by the new physics calculation.
    dependencies=[ROOT/'data/raw/payload_bounds/lines.csv',ROOT/'results/payload_bounds/standard_45_physics.npz',
        ROOT/'results/receiver_design/voc_pm_extension/lines.csv',ROOT/'results/receiver_design/hopping_plan.json',
        ROOT/'results/receiver_design/standard_layers.npz',ROOT/'results/receiver_design/igra_01_layers.npz',
        ROOT/'results/task_completion/igra_01_measured.csv',ROOT/'results/tables/physical_feasibility_config.json',
        ROOT/'scripts/receiver_design_physics.py',ROOT/'scripts/design_payload_receiver.py']
    write=dict(status='verified conditional five-gas design and complete gap audit; experimental milestones open',
        created_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        numerical_verification=verification,tests=tests,pdf=build,
        packages={n:importlib.metadata.version(n) for n in ['numpy','scipy','pandas','matplotlib','pytest','hitran-api','miepython']},
        scope='2/20/100 s by 0/0.0001/0.001 dB; calibration is assumed, not measured. No useful PM/absolute concentration/compliance claim.',
        files={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))},
        inherited_dependencies={p.relative_to(ROOT).as_posix():sha(p) for p in dependencies},
        historical_note='Previous manifests describe prior commit snapshots and are intentionally not rewritten when the manuscript and current audit change.')
    (OUT/'deliverable_manifest.json').write_text(json.dumps(write,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(files=len(write['files']),tests=tests,checks=verification['checks'])))


if __name__=='__main__':main()
