"""Build the updated project without rewriting historical experiment records."""
from pathlib import Path
import subprocess
import sys
import re
import hashlib
import json
import shutil
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/receiver_design'


def main():
    for name in ['verify_receiver_design.py', 'verify_receiver_voc_pm.py', 'report_receiver_design.py', 'report_receiver_voc_pm.py']:
        subprocess.run([sys.executable, str(ROOT/'scripts'/name)], check=True)
    paper = ROOT/'paper'
    for _ in range(2):
        proc = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error',
            '-output-directory=build', 'main.tex'], cwd=paper, capture_output=True, text=True)
        (ROOT/'tmp/receiver_paper_build.txt').write_text(proc.stdout+proc.stderr, encoding='utf-8')
        if proc.returncode:
            raise RuntimeError('LaTeX compilation failed; see tmp/receiver_paper_build.txt')
    log = (paper/'build/main.log').read_text(errors='replace')
    if re.search(r'undefined|Overfull|Rerun to get', log):
        raise RuntimeError('Resolve LaTeX references or overfull boxes before delivery')
    pdf = paper/'build/main.pdf'
    stable = ROOT/'output/pdf/thz_isac_pollutant_sensing_ieee.pdf'
    shutil.copyfile(pdf, stable)
    result = dict(status='built', pages=int(re.search(r'Output written on .*?\((\d+) pages?', log, re.DOTALL).group(1)),
        output=stable.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(stable.read_bytes()).hexdigest(),
        unresolved_references=False, overfull_boxes=False,
        visual_review='Pending separate inspection of every rendered page')
    (OUT/'paper_build.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
