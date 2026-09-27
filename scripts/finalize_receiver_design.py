"""Record the completed receiver extension and its remaining physical limits."""
from pathlib import Path
import sys
import hashlib
import json
import subprocess
import platform
import importlib.metadata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if '--visual-reviewed' not in sys.argv:
        raise RuntimeError('Inspect every rendered PDF page before recording visual review')
    verification = json.loads((OUT/'verification.json').read_text())
    extension = json.loads((OUT/'voc_pm_extension/verification.json').read_text())
    build = json.loads((OUT/'paper_build.json').read_text())
    suites = ET.parse(OUT/'pytest.xml').getroot().findall('testsuite')
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ['tests', 'failures', 'errors', 'skipped']}
    if verification['status'] != 'passed' or extension['status'] != 'passed' or not counts['tests'] or counts['failures'] or counts['errors']:
        raise RuntimeError('Verification or tests not passed')
    if sha(ROOT/build['output']) != build['sha256']:
        raise RuntimeError('PDF does not match successful build')
    build['visual_review'] = 'All rendered pages inspected'
    (OUT/'paper_build.json').write_text(json.dumps(build, indent=2)+'\n', encoding='utf-8')
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'deliverable_manifest.json']
    files += list((ROOT/'scripts').glob('*receiver*.py'))
    files += list((ROOT/'src/thz_isac').glob('*.py'))
    files += [ROOT/p for p in ['.gitattributes', 'pytest.ini', 'README.md', 'AGENTS.md',
        'docs/43_original_proposal_remaining_tasks.md', 'docs/46_critical_calibration_assumption.md',
        'docs/47_receiver_design_and_calibration.md', 'docs/48_expanded_voc_pm_and_20s_calibration.md', 'paper/README.md', 'paper/main.tex',
        'paper/current_study.tex', 'paper/receiver_design.tex', 'paper/receiver_voc_pm.tex', 'paper/payload_recall.tex',
        'paper/payload_bounds.tex', 'paper/build/main.pdf', build['output'], 'tests/test_hopping_receiver.py']]
    result = dict(status='verified conditional receiver study; physical gaps retained',
        created_utc=datetime.now(timezone.utc).isoformat(),
        generation_base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        python=platform.python_version(), packages={n: importlib.metadata.version(n) for n in ['numpy', 'scipy', 'pandas', 'matplotlib', 'pytest', 'hitran-api', 'miepython']},
        tests=dict(command='python -m pytest -q --junitxml=results/receiver_design/pytest.xml', **counts),
        numerical_verification=verification, expanded_target_verification=extension, pdf=build,
        outstanding=['Measured calibration and concentration truth', 'RF power, noise, image rejection and gain stability',
            'Wideband timing and oscillator/pointing uncertainty', 'Useful PM inference', 'Absolute baseline/profile truth and environmental applicability'],
        historical_note='Prior payload manifests describe the preceding commit snapshot. Changed documentation and manuscript are recorded here; original numerical evidence is retained.',
        files={p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(files))})
    (OUT/'deliverable_manifest.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=result['status'], files=len(result['files']), tests=counts['tests'], checks=verification['checks'])))


if __name__ == '__main__':
    main()
