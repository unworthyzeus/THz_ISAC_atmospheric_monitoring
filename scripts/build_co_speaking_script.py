"""Create the concise English speaking script for the CO presentation."""
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, PageBreak
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
TARGET = OUT / 'co_observability_speaking_script.pdf'

# Each block is written to be spoken while the corresponding slide is visible.
SCRIPT = [
    ('1. Our question',
     'We want to know which gases we can identify from their effect on a radio channel between 60 and 1000 gigahertz. We start with carbon monoxide, or CO, and no receiver noise, to understand how its absorption appears in the channel.'),
    ('2. Frequency and path length',
     'We measure the channel across frequency and at different atmospheric path lengths, giving us a matrix called h of f and l. This lets us study both the spectral pattern and how absorption accumulates along the path.'),
    ('3. The channel model',
     'The channel magnitude combines geometric spreading, background atmospheric absorption and extra absorption from CO. Beer-Lambert describes the absorption: power decreases exponentially with optical depth, while amplitude uses half that exponent.'),
    ('4. How we observe the chemical contribution',
     'We compare the measured channel with a reference that has the same geometry, atmosphere and instrument response, but no added CO. Their magnitude ratio gives the chemical amplitude transmission; minus twice its natural logarithm gives the extra chemical optical depth.'),
    ('5. Why separation can be ambiguous',
     'Without a matched reference or enough constraints on the atmosphere, we only observe the combined absorption. Different atmospheric and chemical contributions can produce the same channel, so removing receiver noise does not guarantee a unique answer.'),
    ('6. Why absorption lines are continuous',
     'Molecular energy differences set the line centers, but collisions and thermal motion broaden the response around those centers. A Voigt profile combines collision and Doppler broadening, so a line has a smooth peak and wings, rather than sharp rectangular edges; this broadening remains without receiver noise.'),
    ('7. The CO spectrum',
     'The main form of CO has eight principal rotational lines in this frequency range, with the first near 115 gigahertz. Their relative strengths depend on the gas conditions, and the strongest peak alone does not tell us which measurement band will work best.'),
    ('8. What changing the path length reveals',
     'In this example, the CO cloud lies between 20 and 40 metres, so the extra CO loss grows only while the path crosses that region. Beyond it, the chemical loss stays constant because the path has already crossed the whole cloud, even though other channel losses continue to grow.'),
    ('9. What the numerical example shows',
     'For one part per million of added CO across 20 metres, the model predicts a very small channel change. With exact atmospheric knowledge and calibration, the matched reference recovers the input gas column, but this is a simulation consistency check, not a measured detection limit.'),
    ('10. What we need to know',
     'We need geometry, instrument response and atmospheric conditions, especially temperature, pressure and humidity, to attribute loss to CO. We also need the reference CO level and, to convert a retrieved molecular column into concentration, the cloud length or a spatial model.'),
    ('11. Identifying a gas versus detecting it in practice',
     'First, we ask whether CO creates a spectral response that the allowed atmosphere and other gases cannot reproduce. Then we ask whether that change is large enough to measure; the second question requires an error model, including calibration and environmental uncertainty.'),
    ('12. The next step',
     'Our next decision is how to obtain the reference: through a matched measurement or a constrained atmospheric model. We then vary the uncertain atmospheric quantities and test whether CO remains distinguishable, before extending the method to other gases and mixtures.'),
    ('13. Appendix: the molecular model',
     'The molecular model connects energy levels to transition frequencies, line strengths and profiles to the absorption cross section, and the amount of gas along the path to optical depth. Beer-Lambert then converts optical depth into channel attenuation.'),
    ('14. Appendix: sources',
     'The calculation uses HITRAN spectroscopic parameters, JPL line positions and the ITU atmospheric model. The project notes contain the assumptions, source links and reproducible calculation.'),
]

FONT_DIR = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Georgia', str(FONT_DIR / 'georgia.ttf')))
pdfmetrics.registerFont(TTFont('GeorgiaBold', str(FONT_DIR / 'georgiab.ttf')))
pdfmetrics.registerFontFamily('Georgia', normal='Georgia', bold='GeorgiaBold')
INK = colors.HexColor('#242421')
RUST = colors.HexColor('#B4472B')
MUTED = colors.HexColor('#6E6A61')
PAPER = colors.HexColor('#F8F5EF')
styles = {
    'title': ParagraphStyle('Title', fontName='Georgia', fontSize=24, leading=29, textColor=INK, spaceAfter=7),
    'subtitle': ParagraphStyle('Subtitle', fontName='Georgia', fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=19),
    'heading': ParagraphStyle('Heading', fontName='GeorgiaBold', fontSize=11.2, leading=14, textColor=RUST, spaceAfter=5),
    'body': ParagraphStyle('Body', fontName='Georgia', fontSize=11.2, leading=15.8, textColor=INK, spaceAfter=14, alignment=TA_LEFT),
    'equation': ParagraphStyle('Equation', fontName='Georgia', fontSize=12.5, leading=19, textColor=INK, spaceAfter=14),
    'source': ParagraphStyle('Source', fontName='Georgia', fontSize=8.5, leading=12, textColor=MUTED),
}

def page_design(canvas, document):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont('Georgia', 9)
    canvas.drawString(45, 27, 'CO observability | Speaking script | 15 October 2026')
    canvas.drawRightString(w - 45, 27, str(document.page))
    canvas.restoreState()

document = SimpleDocTemplate(str(TARGET), pagesize=A4, rightMargin=45, leftMargin=45,
                             topMargin=35, bottomMargin=46, title='Observing CO in the channel: speaking script',
                             author='CO observability research', subject='Concise English script for the 14 slide presentation')
story = []
for index, (heading, body) in enumerate(SCRIPT):
    if index in (0, 7):
        if index:
            story.append(PageBreak())
        story.append(Paragraph('Observing CO in the channel', styles['title']))
        story.append(Paragraph('Brief speaking script | Slides 1 to 7' if index == 0 else
                               'Brief speaking script | Slides 8 to 14', styles['subtitle']))
    block = [Paragraph(heading, styles['heading']), Paragraph(body, styles['body'])]
    if index == 3:
        block.append(Paragraph('Key equation: τ<sub>c</sub> = −2 ln(|h| / |h<sub>0</sub>|)', styles['equation']))
    story.append(KeepTogether(block))
story.append(Spacer(1, 2))
story.append(Paragraph('Scientific details: <link href="https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md" color="#B4472B">project foundations and source references</link>.', styles['source']))
document.build(story, onFirstPage=page_design, onLaterPages=page_design)

reader = PdfReader(str(TARGET))
assert len(reader.pages) == 2, f'Unexpected page count: {len(reader.pages)}'
page_text = [page.extract_text() for page in reader.pages]
for index, (heading, body) in enumerate(SCRIPT):
    normalized = re.sub(r'\s+', ' ', page_text[0 if index < 7 else 1])
    assert heading in normalized, f'Missing section: {heading}'
    assert body in normalized, f'Missing script text: {heading}'
assert 'τ' in page_text[0], 'Missing optical depth symbol'
print(f'Created {len(reader.pages)} pages: {TARGET}')
print(f'Spoken word count: {sum(len(body.split()) for _, body in SCRIPT)}')
