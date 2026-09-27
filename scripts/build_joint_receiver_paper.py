"""Build the latest paper without rewriting older experiment manifests."""
from pathlib import Path
import subprocess
import sys
import re
import hashlib
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/joint_receiver_revision'


def main():
    for script in ['verify_joint_receiver.py','report_joint_receiver.py']:
        subprocess.run([sys.executable,str(ROOT/'scripts'/script)],check=True)
    for _ in range(2):
        result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-output-directory=build','main.tex'],
            cwd=ROOT/'paper',capture_output=True,text=True)
        (ROOT/'tmp/joint_receiver_paper_build.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError('Paper compilation failed; inspect tmp/joint_receiver_paper_build.txt')
    log=(ROOT/'paper/build/main.log').read_text(errors='replace')
    if re.search(r'undefined|Overfull|Rerun to get',log):raise RuntimeError('Unresolved references or layout problems')
    destination=ROOT/'output/pdf/thz_isac_pollutant_sensing_ieee.pdf'
    shutil.copyfile(ROOT/'paper/build/main.pdf',destination)
    record=dict(status='built',pages=int(re.search(r'Output written on .*?\((\d+) pages?',log,re.DOTALL).group(1)),
        output=destination.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        unresolved_references=False,overfull_boxes=False,visual_review='Pending rendered page inspection')
    (OUT/'paper_build.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record))


if __name__=='__main__':main()
