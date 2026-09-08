from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "thz_isac_collaboration_grant_proposal.pdf"


NAVY = colors.HexColor("#0B1F33")
INK = colors.HexColor("#182433")
SLATE = colors.HexColor("#526174")
MUTED = colors.HexColor("#738195")
TEAL = colors.HexColor("#0B837A")
TEAL_DARK = colors.HexColor("#075F59")
TEAL_LIGHT = colors.HexColor("#E8F7F4")
CYAN = colors.HexColor("#31C6B4")
BLUE_LIGHT = colors.HexColor("#EDF4FA")
AMBER = colors.HexColor("#D99216")
AMBER_LIGHT = colors.HexColor("#FFF5DE")
GREEN_LIGHT = colors.HexColor("#EAF7EF")
RED_LIGHT = colors.HexColor("#FFF0ED")
LINE = colors.HexColor("#D9E1E8")
PAPER = colors.HexColor("#F8FAFC")
WHITE = colors.white


def register_fonts() -> None:
    font_dir = Path(r"C:\Windows\Fonts")
    pdfmetrics.registerFont(TTFont("Segoe", str(font_dir / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("Segoe-Bold", str(font_dir / "segoeuib.ttf")))
    pdfmetrics.registerFont(TTFont("Segoe-Semibold", str(font_dir / "seguisb.ttf")))
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
    "eyebrow": ParagraphStyle(
        "Eyebrow",
        parent=BASE["Normal"],
        fontName="Segoe-Semibold",
        fontSize=7.2,
        leading=9,
        textColor=TEAL_DARK,
        spaceAfter=4,
        tracking=1.0,
        uppercase=True,
    ),
    "title": ParagraphStyle(
        "Title",
        parent=BASE["Title"],
        fontName="Segoe-Bold",
        fontSize=25,
        leading=28.5,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=8,
    ),
    "subtitle": ParagraphStyle(
        "Subtitle",
        parent=BASE["Normal"],
        fontName="Segoe",
        fontSize=11.2,
        leading=15,
        textColor=SLATE,
        spaceAfter=10,
    ),
    "h1": ParagraphStyle(
        "Heading 1",
        parent=BASE["Heading1"],
        fontName="Segoe-Bold",
        fontSize=17.2,
        leading=21,
        textColor=NAVY,
        spaceBefore=0,
        spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "Heading 2",
        parent=BASE["Heading2"],
        fontName="Segoe-Semibold",
        fontSize=10.8,
        leading=13.5,
        textColor=TEAL_DARK,
        spaceBefore=4,
        spaceAfter=4,
    ),
    "body": ParagraphStyle(
        "Body",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=8.85,
        leading=12.3,
        textColor=INK,
        spaceAfter=5,
    ),
    "body_tight": ParagraphStyle(
        "Body Tight",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=8.35,
        leading=11,
        textColor=INK,
        spaceAfter=2,
    ),
    "small": ParagraphStyle(
        "Small",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=7.55,
        leading=10,
        textColor=SLATE,
    ),
    "small_bold": ParagraphStyle(
        "Small Bold",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=7.65,
        leading=9.8,
        textColor=NAVY,
    ),
    "card_title": ParagraphStyle(
        "Card Title",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=9,
        leading=11,
        textColor=NAVY,
        spaceAfter=2,
    ),
    "card_body": ParagraphStyle(
        "Card Body",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=7.65,
        leading=10.2,
        textColor=SLATE,
    ),
    "hero": ParagraphStyle(
        "Hero",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=11.1,
        leading=15.2,
        textColor=NAVY,
        spaceAfter=0,
    ),
    "quote": ParagraphStyle(
        "Quote",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=9.4,
        leading=12.5,
        textColor=TEAL_DARK,
    ),
    "table_head": ParagraphStyle(
        "Table Header",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=7.4,
        leading=9.2,
        textColor=WHITE,
    ),
    "table_body": ParagraphStyle(
        "Table Body",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=7.35,
        leading=9.6,
        textColor=INK,
    ),
    "table_body_bold": ParagraphStyle(
        "Table Body Bold",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=7.35,
        leading=9.6,
        textColor=NAVY,
    ),
    "reference": ParagraphStyle(
        "Reference",
        parent=BASE["BodyText"],
        fontName="Segoe",
        fontSize=6.8,
        leading=8.7,
        textColor=SLATE,
        leftIndent=9,
        firstLineIndent=-9,
        spaceAfter=2.4,
    ),
    "center_small": ParagraphStyle(
        "Center Small",
        parent=BASE["BodyText"],
        fontName="Segoe-Semibold",
        fontSize=7.5,
        leading=9.2,
        textColor=NAVY,
        alignment=TA_CENTER,
    ),
}


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def section_heading(number: str, title: str) -> Table:
    number_cell = Table(
        [[p(number, "center_small")]],
        colWidths=[10 * mm],
        rowHeights=[10 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), TEAL_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B7E4DD")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    return Table(
        [[number_cell, p(title, "h1")]],
        colWidths=[13 * mm, 160 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )


def callout(
    label: str,
    text: str,
    background=TEAL_LIGHT,
    accent=TEAL,
    width: float = 173 * mm,
) -> Table:
    content = [
        p(f'<font color="{accent.hexval()}"><b>{label.upper()}</b></font>', "eyebrow"),
        p(text, "hero"),
    ]
    return Table(
        [[content]],
        colWidths=[width],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("LINEBEFORE", (0, 0), (0, -1), 3.5, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        ),
    )


def card(title: str, text: str, width: float, background=PAPER, accent=TEAL) -> Table:
    return Table(
        [[[p(title, "card_title"), p(text, "card_body")]]],
        colWidths=[width],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 2.2, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        ),
    )


class SystemDiagram(Flowable):
    def __init__(self, width: float, height: float = 35 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        box_w = 35 * mm
        box_h = 24 * mm
        gap = (self.width - 4 * box_w) / 3
        labels = [
            ("SUB-THZ NTN", "Link budget and\nwideband pilots"),
            ("ATMOSPHERE", "Gas absorption and\nPM scattering"),
            ("CHANNEL DATA", "Frequency selective\nCSI amplitudes"),
            ("DECISION MAP", "Detection limits and\ndesign rules"),
        ]
        fills = [BLUE_LIGHT, TEAL_LIGHT, BLUE_LIGHT, AMBER_LIGHT]
        y = 5 * mm
        canvas.saveState()
        for index, ((heading, body), fill) in enumerate(zip(labels, fills)):
            x = index * (box_w + gap)
            canvas.setFillColor(fill)
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.7)
            canvas.roundRect(x, y, box_w, box_h, 3.2 * mm, fill=1, stroke=1)
            canvas.setFillColor(TEAL_DARK if index != 3 else AMBER)
            canvas.setFont("Segoe-Semibold", 7.4)
            canvas.drawCentredString(x + box_w / 2, y + box_h - 7.5 * mm, heading)
            canvas.setFillColor(SLATE)
            canvas.setFont("Segoe", 6.8)
            for line_index, line in enumerate(body.split("\n")):
                canvas.drawCentredString(
                    x + box_w / 2,
                    y + box_h - (13.2 + line_index * 3.6) * mm,
                    line,
                )
            if index < 3:
                start_x = x + box_w + 1.5 * mm
                end_x = x + box_w + gap - 1.5 * mm
                arrow_y = y + box_h / 2
                canvas.setStrokeColor(CYAN)
                canvas.setFillColor(CYAN)
                canvas.setLineWidth(1.4)
                canvas.line(start_x, arrow_y, end_x, arrow_y)
                canvas.line(end_x, arrow_y, end_x - 2.2 * mm, arrow_y + 1.5 * mm)
                canvas.line(end_x, arrow_y, end_x - 2.2 * mm, arrow_y - 1.5 * mm)
        canvas.restoreState()


def page_chrome(canvas, doc) -> None:
    page_width, page_height = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, page_height - 4.5 * mm, page_width, 4.5 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, 13 * mm, page_width - 18 * mm, 13 * mm)
    canvas.setFont("Segoe", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8.4 * mm, "THz ISAC collaboration grant proposal | 2026/27")
    canvas.drawRightString(page_width - 18 * mm, 8.4 * mm, f"PAGE {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    story = []

    story.extend(
        [
            Spacer(1, 4 * mm),
            p("COLLABORATION GRANT PROJECT  |  2026/27", "eyebrow"),
            p("Atmospheric Monitoring from Sub-THz NTN Links", "title"),
            p(
                "Estimation limits, sensing resources and transferable design rules for integrated sensing and communication",
                "subtitle",
            ),
        ]
    )

    meta = Table(
        [
            [
                p("<b>Student</b><br/>Guillem Moreno García", "small"),
                p("<b>Research activity</b><br/>Introduction to Research I", "small"),
                p("<b>Department</b><br/>Computer Architecture, UPC", "small"),
                p("<b>Academic supervisor</b><br/>Sergi Abadal", "small"),
            ]
        ],
        colWidths=[43.25 * mm] * 4,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        ),
    )
    story.extend(
        [
            meta,
            Spacer(1, 7 * mm),
            callout(
                "Core proposition",
                "Can routine channel observations from a future sub-THz satellite link reveal useful atmospheric information? This project will answer with physical models, quantified uncertainty and explicit detection limits, including a defensible negative result if the signal is too weak.",
            ),
            Spacer(1, 5 * mm),
            SystemDiagram(173 * mm),
            Spacer(1, 2 * mm),
            p("Why this is worth doing", "h2"),
        ]
    )

    three_cards = Table(
        [
            [
                card(
                    "Reuse communication infrastructure",
                    "Tests whether ordinary link observations can carry a secondary sensing signal while making pilot, power and bandwidth costs explicit.",
                    54.7 * mm,
                    BLUE_LIGHT,
                    TEAL,
                ),
                card(
                    "Quantify before deployment",
                    "Replaces a binary promise with detection floors and sensitivity maps that show where the idea is credible and where it is not.",
                    54.7 * mm,
                    TEAL_LIGHT,
                    CYAN,
                ),
                card(
                    "Create reusable research assets",
                    "Produces an auditable simulation and evaluation pipeline that can support later theses, papers and measured channel campaigns.",
                    54.7 * mm,
                    AMBER_LIGHT,
                    AMBER,
                ),
            ]
        ],
        colWidths=[57.65 * mm] * 3,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.extend(
        [
            three_cards,
            Spacer(1, 6 * mm),
            p("Project summary", "h2"),
            p(
                "This project investigates opportunistic atmospheric sensing in 60 to 400 GHz Non-Terrestrial Network links. Molecular species create localized absorption structure, while particulate matter contributes a smoother frequency dependent attenuation. The study will combine layer resolved spectroscopy, a satellite link budget, simulated wideband channel observations and estimation theory to determine whether these signatures remain identifiable under realistic noise and nuisance effects.",
            ),
            p(
                "The central output is not an assumed successful sensor. It is an evidence based map of achievable accuracy, required sensing resources and failure modes. A preliminary reproducible implementation indicates that the declared reference link is information limited, which strengthens the case for a rigorous limits study and for identifying the conditions that would justify a measured follow up campaign.",
            ),
            Spacer(1, 2.5 * mm),
        ]
    )

    criteria = Table(
        [
            [
                p("I  INNOVATION", "table_head"),
                p("II  CONTINUITY AND TRANSFER", "table_head"),
                p("III  METHOD AND FEASIBILITY", "table_head"),
                p("IV  DIGITAL TECHNOLOGIES", "table_head"),
            ],
            [
                p("One physics to link to inference framework", "small"),
                p("Reusable code, data pipeline and design guidance", "small"),
                p("Staged tasks, review gates and measurable outputs", "small"),
                p("Data analysis, simulation, optimization and ML", "small"),
            ],
        ],
        colWidths=[43.25 * mm] * 4,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, 1), BLUE_LIGHT),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        ),
    )
    story.extend([criteria, PageBreak()])

    story.extend(
        [
            section_heading("01", "A differentiated and falsifiable research question"),
            Spacer(1, 3 * mm),
            p(
                "<b>Research gap.</b> Current ISAC studies show that atmospheric phenomena can imprint themselves on satellite links, but pollutant sensing requires a difficult bridge between spectroscopy, propagation, communications and statistical inference. This proposal treats that bridge as a single auditable system and asks what information is actually available after the link budget and nuisance effects are applied.",
            ),
            Spacer(1, 2 * mm),
        ]
    )

    rq_cards = Table(
        [
            [
                card(
                    "RQ1  Detectability",
                    "Which molecular and particulate signatures survive the expected path loss, background absorption and channel uncertainty?",
                    54.7 * mm,
                    PAPER,
                    TEAL,
                ),
                card(
                    "RQ2  Identifiability",
                    "Can narrow gas features be separated from smooth PM attenuation and nuisance terms such as water vapour and oxygen?",
                    54.7 * mm,
                    PAPER,
                    CYAN,
                ),
                card(
                    "RQ3  Design",
                    "What frequency placement, pilot resources, SNR and satellite geometry would make a follow up experiment worthwhile?",
                    54.7 * mm,
                    PAPER,
                    AMBER,
                ),
            ]
        ],
        colWidths=[57.65 * mm] * 3,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.extend(
        [
            rq_cards,
            Spacer(1, 6 * mm),
            p("Method: one chain from physical data to an engineering decision", "h2"),
        ]
    )

    wp_data = [
        [
            p("WORK PACKAGE", "table_head"),
            p("CORE METHOD", "table_head"),
            p("CHECKPOINT AND OUTPUT", "table_head"),
        ],
        [
            p("WP1<br/><b>Atmospheric forward model</b>", "table_body_bold"),
            p(
                "Layered temperature and pressure profiles; HITRAN line parameters; Voigt or Lorentz absorption; exploratory Rayleigh or Mie inspired PM scattering.",
                "table_body",
            ),
            p(
                "Screen target species and retain only bands with physically meaningful contrast. Deliver calibrated spectral templates and an assumptions register.",
                "table_body",
            ),
        ],
        [
            p("WP2<br/><b>NTN link and observations</b>", "table_body_bold"),
            p(
                "Satellite geometry, antenna gains, atmospheric loss, thermal noise and pilot averaging; simulated frequency selective channel observations.",
                "table_body",
            ),
            p(
                "Verify that communication and sensing resources are counted consistently. Deliver a reproducible scenario generator and link diagnostics.",
                "table_body",
            ),
        ],
        [
            p("WP3<br/><b>Inference and separation</b>", "table_body_bold"),
            p(
                "Nuisance aware spectral decomposition; interpretable weighted inversion; regularized regression and machine learning baselines where justified.",
                "table_body",
            ),
            p(
                "Compare simple and advanced estimators on fixed splits and metrics. Deliver error, bias and robustness tables rather than a selected success case.",
                "table_body",
            ),
        ],
        [
            p("WP4<br/><b>Bounds and design rules</b>", "table_body_bold"),
            p(
                "Fisher information and Cramér-Rao bounds; sweeps over SNR, elevation, pilot count, power and frequency placement; optimized probe selection.",
                "table_body",
            ),
            p(
                "Report detection floors and uncertainty. Deliver a regime map that distinguishes feasible, marginal and information limited cases.",
                "table_body",
            ),
        ],
    ]
    wp_table = Table(wp_data, colWidths=[35 * mm, 70 * mm, 68 * mm], repeatRows=1)
    wp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PAPER]),
                ("BOX", (0, 0), (-1, -1), 0.55, NAVY),
                ("INNERGRID", (0, 1), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            wp_table,
            Spacer(1, 6 * mm),
            callout(
                "Evidence boundary",
                "Public measurements and spectroscopic databases will parameterize and test the models, but atmospheric NTN channel observations remain simulated unless a paired measured dataset is obtained. The project will not present simulated retrieval as field validation.",
                BLUE_LIGHT,
                TEAL,
            ),
            Spacer(1, 5 * mm),
            p("Why the approach is innovative", "h2"),
            p(
                "The novelty is not a claim that attenuation sensing is new in isolation. It is the integration of line by line atmospheric physics, an explicit NTN resource model, nuisance aware inversion and analytical information limits in one reproducible workflow. This makes both positive and negative outcomes useful: the study can identify a viable window, quantify the improvement required, or show that a proposed configuration should not advance to costly hardware trials.",
            ),
            Spacer(1, 2 * mm),
            callout(
                "Preliminary readiness",
                "A working prototype, literature base and test suite already exist. The grant period can therefore focus on scientific validation, controlled comparisons and clear research outputs rather than first stage software setup.",
                GREEN_LIGHT,
                TEAL,
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            section_heading("02", "A coherent plan with review gates and measurable outputs"),
            Spacer(1, 3 * mm),
            p(
                "The plan is deliberately staged. Each phase produces a usable artifact and a decision that narrows the following phase, keeping the work viable within one academic semester.",
            ),
            Spacer(1, 2 * mm),
        ]
    )

    timeline_data = [
        [p("TIMING", "table_head"), p("FOCUS", "table_head"), p("REVIEW GATE OR DELIVERABLE", "table_head")],
        [
            p("Weeks 1 to 4", "table_body_bold"),
            p("Literature consolidation, data provenance and atmospheric forward model", "table_body"),
            p("Gate A: select target species and bands only after a line strength and background screen.", "table_body"),
        ],
        [
            p("Weeks 5 to 7", "table_body_bold"),
            p("NTN link budget, slant geometry and channel observation model", "table_body"),
            p("Gate B: freeze reference and stress test scenarios with an explicit resource budget.", "table_body"),
        ],
        [
            p("Weeks 8 to 11", "table_body_bold"),
            p("Spectral separation, interpretable inversion and ML baselines", "table_body"),
            p("Gate C: reduce the target set if parameters are not identifiable; retain negative findings.", "table_body"),
        ],
        [
            p("Weeks 12 to 14", "table_body_bold"),
            p("Information bounds, sensitivity sweeps and probe design", "table_body"),
            p("Detection floor table and design map across SNR, geometry and sensing resources.", "table_body"),
        ],
        [
            p("Weeks 15 to 16", "table_body_bold"),
            p("Synthesis, reproducibility audit and research communication", "table_body"),
            p("Final report, reusable code package and a concrete measured validation roadmap.", "table_body"),
        ],
    ]
    timeline = Table(timeline_data, colWidths=[29 * mm, 67 * mm, 77 * mm], repeatRows=1)
    timeline.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PAPER]),
                ("BOX", (0, 0), (-1, -1), 0.55, NAVY),
                ("INNERGRID", (0, 1), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([timeline, Spacer(1, 6 * mm), p("Concrete deliverables", "h2")])

    deliverables = Table(
        [
            [
                card(
                    "D1  Auditable model",
                    "Layered spectroscopy, PM assumptions and NTN observation generation with unit tests and provenance records.",
                    40.3 * mm,
                    BLUE_LIGHT,
                    TEAL,
                ),
                card(
                    "D2  Estimator benchmark",
                    "Fixed metrics, held out comparisons, uncertainty and failure analysis across interpretable and ML methods.",
                    40.3 * mm,
                    TEAL_LIGHT,
                    CYAN,
                ),
                card(
                    "D3  Design map",
                    "Detection floors versus SNR, elevation, pilot resources and frequency placement, with clear assumptions.",
                    40.3 * mm,
                    AMBER_LIGHT,
                    AMBER,
                ),
                card(
                    "D4  Research package",
                    "A paper style report, reusable figures and tables, and a roadmap for measured validation or scope redirection.",
                    40.3 * mm,
                    GREEN_LIGHT,
                    TEAL,
                ),
            ]
        ],
        colWidths=[43.25 * mm] * 4,
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.extend([deliverables, Spacer(1, 6 * mm)])

    left = [
        p("How success will be judged", "h2"),
        p(
            "<b>Physical consistency.</b> Estimated information must respond correctly to line structure, SNR and geometry.",
            "body_tight",
        ),
        p(
            "<b>Identifiability.</b> Gas, PM and background terms must be separable or explicitly declared confounded.",
            "body_tight",
        ),
        p(
            "<b>Generalization.</b> Data driven baselines use fixed splits and comparable metrics, not hand selected cases.",
            "body_tight",
        ),
        p(
            "<b>Reproducibility.</b> Inputs, assumptions, code, tests and generated outputs remain traceable.",
            "body_tight",
        ),
        p(
            "<b>Decision value.</b> The final result states what should be tested next, what must improve and what should be abandoned.",
            "body_tight",
        ),
    ]
    right = [
        p("Digital competencies in active use", "h2"),
        p(
            "<b>Scientific programming:</b> modular Python implementation and automated tests.<br/>"
            "<b>Data engineering:</b> acquisition, cleaning, provenance and reproducible transformations.<br/>"
            "<b>Numerical methods:</b> spectroscopy, optimization, Fisher information and sensitivity analysis.<br/>"
            "<b>Artificial intelligence:</b> regularized regression and ML baselines, evaluated against interpretable methods.<br/>"
            "<b>Research software:</b> version control, isolated environments, structured results and publication quality visualization.",
            "body_tight",
        ),
        Spacer(1, 2 * mm),
        callout(
            "Architecture fit",
            "The project studies a communication link as a programmable sensing platform: channel estimation, pilot resources, antenna and link budgets, inference pipelines and cross layer design are central computer architecture and network systems concerns.",
            BLUE_LIGHT,
            TEAL,
            79 * mm,
        ),
    ]
    two_col = Table(
        [[left, right]],
        colWidths=[84 * mm, 84 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 5),
                ("LEFTPADDING", (1, 0), (1, -1), 5),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("LINEBEFORE", (1, 0), (1, -1), 0.5, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.extend([two_col, PageBreak()])

    story.extend(
        [
            section_heading("03", "Research continuity, transfer potential and responsible ambition"),
            Spacer(1, 3 * mm),
            p(
                "The immediate value is scientific and engineering knowledge, not an operational environmental product. The project creates a credible transfer path by converting a speculative sensing concept into reusable assets and decision criteria.",
            ),
            Spacer(1, 2 * mm),
            p("Transfer pathway", "h2"),
        ]
    )

    transfer_data = [
        [p("OUTPUT", "table_head"), p("NEAR TERM USER", "table_head"), p("DECISION ENABLED", "table_head")],
        [
            p("Detection and identifiability map", "table_body_bold"),
            p("6G, NTN and ISAC researchers", "table_body"),
            p("Which bands, geometries and sensing resources deserve deeper study.", "table_body"),
        ],
        [
            p("Reproducible simulator and tests", "table_body_bold"),
            p("Research group and future students", "table_body"),
            p("A common baseline for follow up theses, publications and hardware experiments.", "table_body"),
        ],
        [
            p("Validated limitations and evidence gaps", "table_body_bold"),
            p("System designers and project leads", "table_body"),
            p("Whether to invest in calibration, measured channel acquisition or a different sensing geometry.", "table_body"),
        ],
        [
            p("Long term sensing concept", "table_body_bold"),
            p("Network operators and environmental partners", "table_body"),
            p("Only after measured validation: whether communication infrastructure can complement dedicated sensors.", "table_body"),
        ],
    ]
    transfer = Table(transfer_data, colWidths=[50 * mm, 48 * mm, 75 * mm], repeatRows=1)
    transfer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PAPER]),
                ("BOX", (0, 0), (-1, -1), 0.55, NAVY),
                ("INNERGRID", (0, 1), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([transfer, Spacer(1, 6 * mm), p("Risk management", "h2")])

    risk_data = [
        [p("RISK", "table_head"), p("HOW THE DESIGN RESPONDS", "table_head")],
        [
            p("Pollutant signatures are weaker than channel uncertainty", "table_body_bold"),
            p("Report analytical floors and required improvement factors; use an abundant absorber as a positive information control.", "table_body"),
        ],
        [
            p("Gas, PM and background effects are confounded", "table_body_bold"),
            p("Use nuisance aware projections and identifiability diagnostics; reduce the target set instead of forcing a multi pollutant claim.", "table_body"),
        ],
        [
            p("Link or particle assumptions are optimistic", "table_body_bold"),
            p("Sweep assumptions, preserve an explicit register and separate reference, optimistic and stress test scenarios.", "table_body"),
        ],
        [
            p("Simulated observations are mistaken for validation", "table_body_bold"),
            p("Label every evidence source, keep simulated CSI explicit and define measured paired data as the next validation gate.", "table_body"),
        ],
        [
            p("The scope expands beyond one semester", "table_body_bold"),
            p("Prioritize a minimum defensible result, retain review gates and move hardware or field work to a later project.", "table_body"),
        ],
    ]
    risks = Table(risk_data, colWidths=[62 * mm, 111 * mm], repeatRows=1)
    risks.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, RED_LIGHT]),
                ("BOX", (0, 0), (-1, -1), 0.55, NAVY),
                ("INNERGRID", (0, 1), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([risks, Spacer(1, 5 * mm)])

    claims = Table(
        [
            [
                [p("CLAIMS THE PROJECT CAN SUPPORT", "eyebrow"), p("Feasibility under declared assumptions; comparative detection limits; resource trade offs; reproducible negative or positive evidence.", "card_body")],
                [p("CLAIMS IT WILL NOT MAKE", "eyebrow"), p("Operational pollutant retrieval; field validation without paired measurements; legal compliance; universal feasibility across all NTN architectures.", "card_body")],
            ]
        ],
        colWidths=[86.5 * mm, 86.5 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), GREEN_LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), AMBER_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.55, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.55, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )
    story.extend([claims, Spacer(1, 5 * mm), p("Selected references", "h2")])

    references = [
        "[1] S. Aliaga et al., \"Analysis of integrated differential absorption radar and subterahertz satellite communications beyond 6G,\" <i>IEEE JSTARS</i>, vol. 17, pp. 19243-19259, 2024. doi: 10.1109/JSTARS.2024.3480816.",
        "[2] Z. Yang, W. Gao and C. Han, \"A universal attenuation model of terahertz wave in space air ground channel medium,\" <i>IEEE Open Journal of the Communications Society</i>, vol. 5, pp. 2333-2342, 2024. doi: 10.1109/OJCOMS.2024.3386759.",
        "[3] H. Dong and O. B. Akan, \"Martian dust storm detection with THz opportunistic integrated sensing and communication in the Internet of Space,\" <i>IEEE Internet of Things Journal</i>, vol. 13, no. 1, pp. 582-594, 2026. doi: 10.1109/JIOT.2025.3624590.",
        "[4] H. Dong et al., \"Rain rate estimation bounds and weather adaptive pilot allocation for LEO satellite ISAC,\" arXiv:2604.10830, 2026.",
        "[5] I. E. Gordon et al., \"The HITRAN2024 molecular spectroscopic database,\" <i>Journal of Quantitative Spectroscopy and Radiative Transfer</i>, vol. 353, 109807, 2026. doi: 10.1016/j.jqsrt.2026.109807.",
        "[6] R. V. Kochanov et al., \"HITRAN Application Programming Interface: A comprehensive approach to working with spectroscopic data,\" <i>Journal of Quantitative Spectroscopy and Radiative Transfer</i>, vol. 177, pp. 15-30, 2016. doi: 10.1016/j.jqsrt.2016.03.005.",
        "[7] International Telecommunication Union, \"Attenuation by atmospheric gases and related effects,\" Recommendation ITU-R P.676-13, 2022; and \"Reference standard atmospheres,\" Recommendation ITU-R P.835-7, 2024.",
    ]
    ref_rows = []
    for index in range(0, len(references), 2):
        left_ref = p(references[index], "reference")
        right_ref = p(references[index + 1], "reference") if index + 1 < len(references) else ""
        ref_rows.append([left_ref, right_ref])
    reference_table = Table(
        ref_rows,
        colWidths=[84.5 * mm, 84.5 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 5),
                ("LEFTPADDING", (1, 0), (1, -1), 5),
                ("RIGHTPADDING", (1, 0), (1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        ),
    )
    story.extend([reference_table, Spacer(1, 3 * mm), p("The proposal is intentionally ambitious in method and conservative in claims.", "quote")])

    return story


def build_pdf() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title="Atmospheric Monitoring from Sub-THz NTN Links",
        author="Guillem Moreno García",
        subject="Collaboration grant research proposal 2026/27",
        creator="ReportLab",
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
    doc.addPageTemplates([PageTemplate(id="proposal", frames=[frame], onPage=page_chrome)])
    doc.build(build_story())


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
