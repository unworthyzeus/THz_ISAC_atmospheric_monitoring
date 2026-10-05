"""Render the teaching deck's mathematical equations as cropped vector assets."""
from pathlib import Path
import json
import subprocess
import os
import fitz

ROOT = Path(__file__).resolve().parents[1]
WORKED = os.environ.get('DECK_PROFILE') == 'worked'
BUILD = ROOT / ('tmp/zenith_worked_deck' if WORKED else 'tmp/zenith_deck')
ASSETS = BUILD / 'equations'
ASSETS.mkdir(parents=True, exist_ok=True)
slides = json.loads((BUILD/'slides.json').read_text(encoding='utf-8'))
equations = [(i+1,s['latex']) for i,s in enumerate(slides) if s.get('latex')]
source = r'''\documentclass{article}
\usepackage[paperwidth=24in,paperheight=5in,margin=0.2in]{geometry}
\usepackage{amsmath,amssymb,xcolor}
\definecolor{eqcolor}{HTML}{126B76}
\pagestyle{empty}
\begin{document}
\color{eqcolor}\fontsize{27}{36}\selectfont
'''
source += ('\n'+r'\newpage'+'\n').join('% Slide '+str(i)+'\n'+r'\[\displaystyle '+tex+r'\]'+'\n' for i,tex in equations)
source += '\n'+r'\end{document}'+'\n'
(ASSETS/'equations.tex').write_text(source,encoding='utf-8')
result = subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','equations.tex'],cwd=ASSETS,capture_output=True,text=True)
(ASSETS/'compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
if result.returncode:
    raise RuntimeError('Equation compilation failed: '+result.stdout[-2500:])
assets = {}
with fitz.open(ASSETS/'equations.pdf') as doc:
    assert len(doc)==len(equations)
    for page,(number,tex) in zip(doc,equations):
        boxes=[fitz.Rect(span['bbox']) for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans']]
        bounds=boxes[0]
        for box in boxes[1:]: bounds |= box
        page.set_cropbox((bounds+(-12,-12,12,12)) & page.rect)
        filename=f'equation-{number:02d}.svg'
        (ASSETS/filename).write_text(page.get_svg_image(text_as_path=True),encoding='utf-8')
        assets[str(number)]={'file':filename,'width':page.rect.width,'height':page.rect.height,'latex':tex}
(BUILD/'equations.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
(ROOT/'output/presentations'/('zenith_acetonitrile_worked_equations.tex' if WORKED else 'zenith_acetonitrile_equations.tex')).write_text(source,encoding='utf-8')
print(f'Rendered {len(equations)} mathematical equations')
