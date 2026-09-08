from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "thz_isac_collaboration_grant_proposal_revised.pdf"

BLACK = colors.HexColor("#171717")
GRAY = colors.HexColor("#5D636B")
LIGHT_GRAY = colors.HexColor("#F2F3F4")
RULE = colors.HexColor("#B9BDC2")
ACCENT = colors.HexColor("#284B63")


def register_fonts() -> None:
    font_dir = Path(r"C:\Windows\Fonts")
    pdfmetrics.registerFont(TTFont("Segoe", str(font_dir / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("Segoe-Bold", str(font_dir / "segoeuib.ttf")))
    pdfmetrics.registerFont(TTFont("Segoe-Italic", str(font_dir / "segoeuii.ttf")))
    pdfmetrics.registerFontFamily(
        "Segoe",
        normal="Segoe",
        bold="Segoe-Bold",
        italic="Segoe-Italic",
        boldItalic="Segoe-Bold",
    )


register_fonts()

BASE = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle(
        "Title",
        parent=BASE["Title"],
        fontName="Segoe-Bold",
        fontSize=17.5,
        leading=22,
        textColor=BLACK,
        alignment=TA_LEFT,
        spaceAfter=5,
    ),
    "meta": ParagraphStyle(
        "Meta",
        parent=BASE["Normal"],
        fontName="Segoe",
        fontSize=8.5,
        leading=11,
        textColor=GRAY,
        spaceAfter=10,
    ),
    "h1": ParagraphStyle(
        "Heading 1",
        parent=BASE["Heading1"],
        fontName="Segoe-Bold",
        fontSize=12.5,
        leading=15.5,
        textColor=BLACK,
        spaceBefore=6,
        spaceAfter=4,
    ),
    "h2": ParagraphStyle(
        "Heading 2",
        parent=BASE["Heading2"],
        fontName="Segoe-Bold",
        fontSize=10.2,
        leading=13,
        textColor=BLACK,
        spaceBefore=4,
        spaceAfter=2,
    ),
    "body": ParagraphStyle(
        "Body",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=9.25,
        leading=12.6,
        textColor=BLACK,
        spaceAfter=5,
    ),
    "bullet": ParagraphStyle(
        "Bullet",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=9.1,
        leading=12.2,
        textColor=BLACK,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2.5,
    ),
    "task": ParagraphStyle(
        "Task",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=8.9,
        leading=12,
        textColor=BLACK,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=3,
    ),
    "table_head": ParagraphStyle(
        "Table Header",
        parent=BASE["BodyText"],
        fontName="Segoe-Bold",
        fontSize=8.1,
        leading=10,
        textColor=BLACK,
    ),
    "table_body": ParagraphStyle(
        "Table Body",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=7.9,
        leading=10.3,
        textColor=BLACK,
    ),
    "reference": ParagraphStyle(
        "Reference",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=6.8,
        leading=8.5,
        textColor=GRAY,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=1.5,
    ),
    "note": ParagraphStyle(
        "Note",
        parent=BASE["BodyText"],
        fontName="Segoe-Italic",
        fontSize=8.3,
        leading=11,
        textColor=GRAY,
        spaceAfter=4,
    ),
}


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def page_chrome(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(ACCENT)
    canvas.setLineWidth(1.3)
    canvas.line(20 * mm, height - 13 * mm, width - 20 * mm, height - 13 * mm)
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.setFont("Segoe", 7)
    canvas.setFillColor(GRAY)
    canvas.drawString(20 * mm, 9 * mm, "THz ISAC research proposal")
    canvas.drawRightString(width - 20 * mm, 9 * mm, str(doc.page))
    canvas.restoreState()


def bullet(text: str) -> Paragraph:
    return p(f"•&nbsp;&nbsp;{text}", "bullet")


def task(number: str, title: str, text: str) -> Paragraph:
    return p(f"<b>{number}. {title}.</b> {text}", "task")


def build_story() -> list:
    story = [
        Spacer(1, 4 * mm),
        p(
            "Estimation Limits of Atmospheric Monitoring with Integrated Sensing and Communication in Sub-THz Non-Terrestrial Networks",
            "title",
        ),
        p(
            "Guillem Moreno García  |  Department of Computer Architecture, UPC<br/>Academic supervisor: Sergi Abadal",
            "meta",
        ),
        p("Abstract", "h1"),
        p(
            "This project studies whether channel estimates already generated by future sub-THz Non-Terrestrial Network links could also provide useful atmospheric information. Molecular species produce localized absorption features, while particulate matter produces a smoother frequency dependent attenuation. The work will combine a stratified atmosphere model, spectroscopic data, a satellite link budget, simulated wideband channel observations and statistical estimation methods.",
        ),
        p(
            "The main goal is to quantify feasibility rather than assume that pollutant recovery will succeed. The study will calculate estimation limits and evaluate how performance changes with frequency, signal to noise ratio, satellite elevation and pilot resources. If the pollutant signatures are too weak or cannot be separated, that result will be reported directly together with the improvement required for a future system.",
        ),
        p(
            "The project extends recent work on atmospheric integrated sensing and communication by treating molecular absorption, particulate scattering, link uncertainty and estimator performance in a common framework. Its outputs will include reusable software, detection limits and a clear basis for later research, such as a master's thesis, a publication or a measured validation campaign.",
        ),
        p("Objectives and relevance", "h1"),
        bullet(
            "Build a physically traceable sub-THz atmospheric channel model using standard atmospheric profiles, HITRAN line parameters and a declared particulate matter model."
        ),
        bullet(
            "Generate wideband channel observations from an explicit NTN link budget and quantify the effect of noise, geometry and pilot allocation."
        ),
        bullet(
            "Compare interpretable inversion methods with regularized regression or machine learning baselines, using the same data splits and metrics."
        ),
        bullet(
            "Determine detection floors and identify the frequency and resource conditions under which further experimental work would be justified."
        ),
        p("Research tasks", "h1"),
        task(
            "Task 1",
            "Atmospheric channel modelling",
            "Develop a layered tropospheric profile in which pressure, temperature and molecular density vary with altitude. Extract relevant line positions, strengths and broadening coefficients from HITRAN, integrate molecular absorption along the satellite slant path and model the smoother attenuation caused by particulate matter.",
        ),
        task(
            "Task 2",
            "NTN link and channel observation model",
            "Define the satellite geometry, antenna gains, transmit power, receiver noise and frequency probes. Simulate wideband channel observations after atmospheric attenuation and pilot averaging. The sensing resources will be counted explicitly so that communication and sensing assumptions remain consistent.",
        ),
        task(
            "Task 3",
            "Estimation and feature separation",
            "Separate localized gas absorption from broad attenuation and background terms such as water vapour and oxygen. Evaluate weighted fitting, regularized regression and selected machine learning methods. Report error, bias and robustness, including cases where the parameters are not identifiable.",
        ),
        task(
            "Task 4",
            "Performance limits and sensitivity",
            "Derive Fisher information and Cramér-Rao bounds, then study sensitivity to link SNR, elevation, pilot count, power and frequency placement. Report gas and particulate detection floors in physical units and compare them only as scale references, not as a claim of environmental compliance.",
        ),
        PageBreak(),
        Spacer(1, 10 * mm),
        p("Expected outcomes and research continuity", "h1"),
            bullet("A reproducible Python implementation of the atmospheric model, link budget and estimation pipeline."),
            bullet("Detection floors and sensitivity plots for the selected gases, particulate matter and link scenarios."),
            bullet("A fair comparison between simple estimators and selected machine learning baselines."),
            bullet("A concise report stating what works, what does not, and which measured data would be required next."),
            p(
                "These outputs can be reused by the research group in later student projects and publications. They also provide practical guidance on frequency selection, pilot allocation and the value of acquiring measured sub-THz channel data. The work fits the Computer Architecture Department through its focus on channel estimation, communication resources, signal processing, programmable sensing and reproducible software.",
            ),
            p("Digital methods", "h1"),
            p(
                "The project will make active use of Python, scientific data processing, numerical optimization, statistical learning, automated testing, version control and publication quality visualization. HITRAN and public atmospheric measurements will be used as external inputs where applicable.",
            ),
            p("Risks and scope", "h1"),
            bullet(
                "If pollutant signatures are below channel uncertainty, the work will report analytical bounds and the improvement required rather than claim successful retrieval."
            ),
            bullet(
                "If several targets are not identifiable, the study will reduce the target set and keep the confounding analysis as a result."
            ),
            bullet(
                "Particulate matter properties and vertical pollutant profiles will be treated as explicit assumptions and tested through sensitivity analysis."
            ),
            bullet(
                "Atmospheric NTN channel observations are simulated. The proposal does not claim field validation, operational monitoring or legal compliance."
            ),
            p("References", "h1"),
    ]

    references = [
        "[1] S. Aliaga et al., \"Analysis of Integrated Differential Absorption Radar and Subterahertz Satellite Communications Beyond 6G,\" <i>IEEE Journal of Selected Topics in Applied Earth Observations and Remote Sensing</i>, vol. 17, pp. 19243-19259, 2024. doi: 10.1109/JSTARS.2024.3480816.",
        "[2] Z. Yang, W. Gao and C. Han, \"A Universal Attenuation Model of Terahertz Wave in Space Air Ground Channel Medium,\" <i>IEEE Open Journal of the Communications Society</i>, vol. 5, pp. 2333-2342, 2024. doi: 10.1109/OJCOMS.2024.3386759.",
        "[3] H. Dong and O. B. Akan, \"Martian Dust Storm Detection With THz Opportunistic Integrated Sensing and Communication in the Internet of Space,\" <i>IEEE Internet of Things Journal</i>, vol. 13, no. 1, pp. 582-594, 2026. doi: 10.1109/JIOT.2025.3624590.",
        "[4] H. Dong et al., \"Rain Rate Estimation Bounds and Weather Adaptive Pilot Allocation for LEO Satellite ISAC,\" arXiv:2604.10830, 2026.",
        "[5] I. E. Gordon et al., \"The HITRAN2024 Molecular Spectroscopic Database,\" <i>Journal of Quantitative Spectroscopy and Radiative Transfer</i>, vol. 353, 109807, 2026. doi: 10.1016/j.jqsrt.2026.109807.",
        "[6] International Telecommunication Union, \"Attenuation by Atmospheric Gases and Related Effects,\" Recommendation ITU-R P.676-13, 2022, and \"Reference Standard Atmospheres,\" Recommendation ITU-R P.835-7, 2024.",
    ]
    reference_rows = []
    for index in range(0, len(references), 2):
        reference_rows.append(
            [
                p(references[index], "reference"),
                p(references[index + 1], "reference") if index + 1 < len(references) else "",
            ]
        )
    reference_table = Table(
        reference_rows,
        colWidths=[83 * mm, 83 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 4),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        ),
    )
    story.append(reference_table)
    return story


def build_pdf() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title="Estimation Limits of Atmospheric Monitoring with ISAC in Sub-THz NTN",
        author="Guillem Moreno García",
        subject="Collaboration grant research proposal 2026/27",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="main",
    )
    doc.addPageTemplates([PageTemplate(id="plain", frames=[frame], onPage=page_chrome)])
    doc.build(build_story())


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
