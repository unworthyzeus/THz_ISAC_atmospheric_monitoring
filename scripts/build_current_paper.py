"""Build current tables/PDF and copy the verified build to its stable location."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def main():
    subprocess.run([sys.executable, str(ROOT / "scripts/build_closure_tables.py")], check=True)
    (PAPER / "build").mkdir(exist_ok=True)
    for _ in range(2):
        result = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                                 "-output-directory=build", "main.tex"], cwd=PAPER,
                                capture_output=True, text=True)
        (PAPER / "build/closure_build_stdout.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError("LaTeX failed; inspect paper/build/closure_build_stdout.txt")
    log = (PAPER / "build/main.log").read_text(errors="replace")
    if re.search(r"undefined|Overfull|Rerun to get", log):
        raise RuntimeError("Unresolved reference or overfull content in final LaTeX log")
    pdf = PAPER / "build/main.pdf"
    stable = ROOT / "output/pdf/thz_isac_pollutant_sensing_ieee.pdf"
    stable.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf, stable)
    pages = int(re.search(r"Output written on .*?\((\d+) pages?", log, re.DOTALL).group(1))
    result = dict(status="built", pages=pages, output=stable.relative_to(ROOT).as_posix(),
                  sha256=hashlib.sha256(stable.read_bytes()).hexdigest(),
                  unresolved_references=False, overfull_boxes=False,
                  visual_review="Render and inspect all pages separately; compilation is not visual review")
    (ROOT / "results/five_task_closure/paper_build.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
