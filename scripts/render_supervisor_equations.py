"""Compile real LaTeX and render cropped vector equation assets for slides."""
from pathlib import Path
import json
import subprocess
import fitz

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'tmp/supervisor_deck'
ASSETS=BUILD/'equations'
ASSETS.mkdir(exist_ok=True)
slides=json.loads((BUILD/'slides.json').read_text(encoding='utf-8'))
equations=[(i+1,s['latex']) for i,s in enumerate(slides) if s.get('latex')]
source=r'''\documentclass{article}
\usepackage[paperwidth=20in,paperheight=3in,margin=0.2in]{geometry}
\usepackage{amsmath,amssymb,xcolor}
\definecolor{eqcolor}{HTML}{126B76}
\pagestyle{empty}
\begin{document}
\color{eqcolor}\fontsize{24}{32}\selectfont
'''
source+=('\n'+r'\newpage'+'\n').join('% Slide '+str(i)+'\n'+r'\[\displaystyle '+tex+r'\]'+'\n' for i,tex in equations)
source+='\n'+r'\end{document}'+'\n'
(ASSETS/'equations.tex').write_text(source,encoding='utf-8')
result=subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','equations.tex'],cwd=ASSETS,capture_output=True,text=True)
(ASSETS/'compile.log').write_text(result.stdout+result.stderr,encoding='utf-8')
if result.returncode:raise RuntimeError('LaTeX equation compilation failed: '+result.stdout[-2500:])
doc=fitz.open(ASSETS/'equations.pdf')
assert len(doc)==len(equations)
assets={}
for page,(number,tex) in zip(doc,equations):
    boxes=[fitz.Rect(span['bbox']) for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans']]
    bounds=boxes[0]
    for rect in boxes[1:]:bounds|=rect
    bounds+=(-12,-12,12,12)
    page.set_cropbox(bounds & page.rect)
    stem=f'equation-{number:02d}'
    (ASSETS/(stem+'.svg')).write_text(page.get_svg_image(text_as_path=True),encoding='utf-8')
    page.get_pixmap(matrix=fitz.Matrix(3,3),alpha=True).save(ASSETS/(stem+'.png'))
    assets[str(number)]={'file':stem+'.svg','width':page.rect.width,'height':page.rect.height,'latex':tex}
(BUILD/'equations.json').write_text(json.dumps(assets,indent=2),encoding='utf-8')
(ROOT/'output/presentations/supervisor_equations.tex').write_text(source,encoding='utf-8')
print(f'Compiled and rendered {len(equations)} LaTeX equations')
