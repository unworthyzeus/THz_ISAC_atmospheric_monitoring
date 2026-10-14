"""Package the reviewed CO slide renders as a bookmarked reading PDF."""
from pathlib import Path
import json
import os
import fitz

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'tmp/co_observability_deck'
slides = json.loads((BUILD / 'slides.json').read_text(encoding='utf-8'))
document = fitz.open()
for number, slide in enumerate(slides, 1):
    page = document.new_page(width=960, height=540)
    page.insert_image(page.rect, filename=str(BUILD / f'renders/slide-{number:02d}.png'))
    if number == len(slides):
        refs = {ref['label']: ref['url'] for ref in slide['sources']}
        for row, key in enumerate(['hitran', 'jpl', 'itu', 'nist', 'local']):
            top = 170 + row * 83
            page.insert_link({'kind': fitz.LINK_URI,
                              'from': fitz.Rect(64, top, 434, top + 45) * .75,
                              'uri': refs[key]})
document.set_toc([[1, slide['title'].replace('\n', ' '), number]
                  for number, slide in enumerate(slides, 1)])
document.set_metadata({'title': 'Observing CO in the channel',
                       'subject': 'Absorption and atmospheric separation in h(f, l), 60 to 1000 GHz',
                       'keywords': 'CO, spectroscopy, atmospheric absorption, observability'})
name = Path(os.environ.get('CO_DECK_NAME', 'co_observability_editorial_v2.pptx')).with_suffix('.pdf').name
target = ROOT / 'output/presentations' / name
document.save(target, deflate=True)
document.close()
with fitz.open(target) as check:
    assert len(check) == len(slides) == 14
    assert len(check.get_toc()) == len(slides)
    assert len(check[-1].get_links()) == 5
    assert all(len(page.get_images()) == 1 for page in check)
print(f'Created {len(slides)} bookmarked pages: {target}')
