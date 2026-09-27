"""Create the reading PDF from the reviewed final slide renders."""
from pathlib import Path
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
slides = json.loads((ROOT / 'tmp/supervisor_deck/slides.json').read_text(encoding='utf-8'))
document = fitz.open()
for number, slide in enumerate(slides, 1):
    picture = ROOT / f'tmp/supervisor_deck/renders-detailed/slide-{number:02d}.png'
    page = document.new_page(width=960, height=540)
    page.insert_image(page.rect, filename=str(picture))
document.set_toc([[1, slide['title'], number] for number, slide in enumerate(slides, 1)])
document.set_metadata({'title': 'Sub-THz atmospheric sensing: supervisor research review',
                       'author': 'Guillem Moreno Garcia',
                       'subject': 'All eleven tasks, methods, conditional results and remaining problems',
                       'keywords': 'ISAC, VOC, PM2.5, PM10, calibration, recall'})
target = ROOT / 'output/presentations/sub_thz_isac_supervisor_review_legends.pdf'
document.save(target, deflate=True)
document.close()
with fitz.open(target) as check:
    assert len(check) == len(slides) == 39
    assert len(check.get_toc()) == 39
print(f'Created PDF reading copy with 39 bookmarked slides: {target}')
