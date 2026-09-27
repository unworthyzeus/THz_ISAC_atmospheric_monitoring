"""Record the reviewed deliverable without altering historical snapshots."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/payload_bounds'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if '--visual-reviewed' not in sys.argv:
        raise RuntimeError('Render and inspect every final PDF page before recording visual review')
    verification = json.loads((OUT/'verification.json').read_text())
    if verification['status'] != 'passed':
        raise RuntimeError('Numerical verification not passed')
    suites = ET.parse(OUT/'report/pytest.xml').getroot().findall('testsuite')
    totals = {key: sum(int(s.get(key, 0)) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    if totals['tests'] == 0 or totals['failures'] or totals['errors']:
        raise RuntimeError('Full test report missing or failed')
    build_path = OUT/'report/paper_build.json'
    build = json.loads(build_path.read_text())
    if sha(ROOT/build['output']) != build['sha256']:
        raise RuntimeError('PDF differs from successful build')
    build['visual_review'] = 'All rendered pages inspected; layout and labels passed'
    build_path.write_text(json.dumps(build, indent=2)+'\n')
    names = ['AGENTS.md', 'README.md', 'paper/README.md', 'paper/current_study.tex', 'paper/payload_bounds.tex',
        'paper/payload_bounds_rows.tex', 'paper/payload_bounds_numbers.tex', 'scripts/build_current_paper.py',
        'docs/43_original_proposal_remaining_tasks.md', 'docs/44_payload_information_derivation.md',
        'docs/45_payload_bounds_results.md', 'docs/46_critical_calibration_assumption.md', 'tests/test_payload_information.py',
        'output/pdf/thz_isac_pollutant_sensing_ieee.pdf', 'paper/build/main.pdf']
    files = [ROOT/name for name in names]
    files += list((ROOT/'scripts').glob('*payload*.py'))
    files += list((ROOT/'src/thz_isac').glob('*.py'))
    files += [p for p in OUT.rglob('*') if p.is_file() and p.name != 'deliverable_manifest.json' and p.suffix != '.log']
    # Actual acquired records, raw hashes and source URL are retained in the
    # acquisition manifest; large raw files remain reproducible ignored inputs.
    versions = {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'pandas', 'matplotlib', 'pytest', 'hitran-api', 'miepython', 'itur']}
    result = dict(status='verified conditional computational study', created_utc=datetime.now(timezone.utc).isoformat(),
        git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        python=platform.python_version(), packages=versions,
        tasks='Payload extensions of original 4.1, 4.2 and 4.3; field compliance and moving receiver implementation remain open',
        tests=dict(command='PYTHONPATH=src python -m pytest -q --junitxml=results/payload_bounds/report/pytest.xml',
                   passed=totals['tests']-totals['skipped'], **totals), numerical_verification=verification,
        pdf=build, files={p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(files))})
    (OUT/'report/deliverable_manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], files=len(result['files']), pages=build['pages'], checks=verification['checks'])))


if __name__ == '__main__':
    main()
