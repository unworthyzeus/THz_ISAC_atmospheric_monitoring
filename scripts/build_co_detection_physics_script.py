"""Create the English speaking script matched to the CO detection physics deck."""
from pathlib import Path
import json
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, KeepTogether, PageBreak
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SLIDES = json.loads((ROOT / 'tmp/co_detection_physics_deck/slides.json').read_text(encoding='utf-8'))
TARGET = ROOT / 'output/pdf/co_detection_physics_speaking_script.pdf'
TARGET.parent.mkdir(parents=True, exist_ok=True)
FONT_DIR = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Georgia', str(FONT_DIR / 'georgia.ttf')))
pdfmetrics.registerFont(TTFont('GeorgiaBold', str(FONT_DIR / 'georgiab.ttf')))
pdfmetrics.registerFontFamily('Georgia', normal='Georgia', bold='GeorgiaBold')
INK = colors.HexColor('#242421')
RUST = colors.HexColor('#B4472B')
MUTED = colors.HexColor('#6E6A61')
PAPER = colors.HexColor('#F8F5EF')
styles = {
    'title': ParagraphStyle('Title', fontName='Georgia', fontSize=25, leading=30, textColor=INK, spaceAfter=7),
    'subtitle': ParagraphStyle('Subtitle', fontName='Georgia', fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=20),
    'heading': ParagraphStyle('Heading', fontName='GeorgiaBold', fontSize=11.2, leading=14, textColor=RUST, spaceAfter=5),
    'body': ParagraphStyle('Body', fontName='Georgia', fontSize=11.2, leading=15.8, textColor=INK, spaceAfter=15),
    'equation': ParagraphStyle('Equation', fontName='Georgia', fontSize=13, leading=20, textColor=INK, spaceAfter=15),
    'source': ParagraphStyle('Source', fontName='Georgia', fontSize=9, leading=13, textColor=MUTED),
}


def page_design(canvas, document):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont('Georgia', 9)
    canvas.drawString(45, 27, 'CO detection and absorption physics | Speaking script')
    canvas.drawRightString(w - 45, 27, str(document.page))
    canvas.restoreState()


document = SimpleDocTemplate(str(TARGET), pagesize=A4, rightMargin=45, leftMargin=45,
                             topMargin=35, bottomMargin=47,
                             title='Can we detect CO? Speaking script',
                             author='CO observability research',
                             subject='English script for the 17 slide CO detection and physics presentation')
story = []
groups = [(0, 6), (6, 12), (12, 17)]
for group_index, (start, stop) in enumerate(groups):
    if group_index:
        story.append(PageBreak())
    story.append(Paragraph('Can we detect CO?', styles['title']))
    story.append(Paragraph(f'Speaking script | Slides {start + 1} to {stop}', styles['subtitle']))
    for index in range(start, stop):
        slide = SLIDES[index]
        block = [Paragraph(escape(f'{index + 1}. {slide["title"]}'), styles['heading']),
                 Paragraph(escape(slide['script']), styles['body'])]
        if index == 9:
            block.append(Paragraph('Key equation: τ<sub size="9" rise="3">c</sub> = −2 ln(|h| / |h<sub size="9" rise="3">0</sub>|)', styles['equation']))
        story.append(KeepTogether(block))
story.append(Paragraph('Slides 16 and 17 are supporting material for questions. Scientific qualifications and links are in the presentation notes and the '
                       '<link href="https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/main/docs/61_co_detection_physics_2026_10_15.md" color="#B4472B">research record</link>.', styles['source']))
document.build(story, onFirstPage=page_design, onLaterPages=page_design)

reader = PdfReader(str(TARGET))
assert len(reader.pages) == 3, f'Unexpected page count: {len(reader.pages)}'
for page, (start, stop) in zip(reader.pages, groups):
    normalized = re.sub(r'\s+', ' ', page.extract_text())
    for index in range(start, stop):
        slide = SLIDES[index]
        assert f'{index + 1}. {slide["title"]}' in normalized, f'Missing heading {index + 1}'
        assert slide['script'] in normalized, f'Missing spoken text {index + 1}'
assert 'τ' in reader.pages[1].extract_text()
print(f'Created {len(reader.pages)} pages: {TARGET}')
print(f'Spoken word count: {sum(len(slide["script"].split()) for slide in SLIDES)}')
