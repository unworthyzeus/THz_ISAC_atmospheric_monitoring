"""Package the reviewed slide renders as a bookmarked reading PDF."""
from pathlib import Path
import json
import os
import fitz

ROOT=Path(__file__).resolve().parents[1]
WORKED=os.environ.get('DECK_PROFILE')=='worked'
BUILD=ROOT/('tmp/zenith_worked_deck' if WORKED else 'tmp/zenith_deck')
slides=json.loads((BUILD/'slides.json').read_text(encoding='utf-8'))
document=fitz.open()
for number,slide in enumerate(slides,1):
    page=document.new_page(width=960,height=540)
    page.insert_image(page.rect,filename=str(BUILD/f'renders/slide-{number:02d}.png'))
document.set_toc([[1,s['title'].replace('\n',' '),i] for i,s in enumerate(slides,1)])
document.set_metadata({'title':'Detecting acetonitrile at 90 degrees elevation',
                       'subject':'A conditional LEO example with explicit observations, matrices and detection decisions',
                       'keywords':'CH3CN, ISAC, LEO, OFDM, spectroscopy, calibration'})
target=ROOT/'output/presentations'/('zenith_acetonitrile_worked_example.pdf' if WORKED else 'zenith_acetonitrile_tutorial.pdf')
document.save(target,deflate=True)
document.close()
with fitz.open(target) as check:
    assert len(check)==len(slides)==(34 if WORKED else 38)
    assert len(check.get_toc())==len(slides)
print(f'Created {len(slides)} bookmarked pages: {target}')
