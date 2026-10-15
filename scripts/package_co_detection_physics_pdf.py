"""Package reviewed slide renders as the reading PDF for CO detection physics."""
from pathlib import Path
import json
import os

import fitz

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'tmp/co_detection_physics_deck'
slides = json.loads((BUILD / 'slides.json').read_text(encoding='utf-8'))
document = fitz.open()
for number, slide in enumerate(slides, 1):
    page = document.new_page(width=960, height=540)
    page.insert_image(page.rect, filename=str(BUILD / f'renders/slide-{number:02d}.png'))
    if number == len(slides):
        refs = {ref['label']: ref['url'] for ref in slide['sources']}
        for row, key in enumerate(['rotor', 'coherence', 'hitran', 'jpl', 'itu', 'local']):
            top = 171 + row * 72
            page.insert_link({'kind': fitz.LINK_URI,
                              'from': fitz.Rect(64, top, 494, top + 44) * .75,
                              'uri': refs[key]})

document.set_toc([[1, slide['title'].replace('\n', ' '), number]
                  for number, slide in enumerate(slides, 1)])
document.set_metadata({'title': 'Can we detect CO? The physics of absorption',
                       'subject': 'CO detectability and the physical origin of spectral line shapes',
                       'keywords': 'CO, absorption, coherence, Doppler, Voigt, channel'})
name = Path(os.environ.get('CO_PHYSICS_DECK_NAME', 'co_detection_physics_v2.pptx')).with_suffix('.pdf').name
target = ROOT / 'output/presentations' / name
document.save(target, deflate=True)
document.close()
with fitz.open(target) as check:
    assert len(check) == len(slides) == 17
    assert len(check.get_toc()) == len(slides)
    assert len(check[-1].get_links()) == 6
    assert all(len(page.get_images()) == 1 for page in check)
print(f'Created {len(slides)} bookmarked pages: {target}')
