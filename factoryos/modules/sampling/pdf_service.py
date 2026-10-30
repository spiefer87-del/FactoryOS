from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, LongTable, CondPageBreak
from .document_service import document_data


def _register_fonts():
    font_dir = Path(__file__).resolve().parents[2] / "static" / "fonts" / "sampling"
    for name, filename in (("Sampling", "DejaVuSans.ttf"), ("Sampling-Bold", "DejaVuSans-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    pdfmetrics.registerFontFamily("Sampling", normal="Sampling", bold="Sampling-Bold")


def build_pdf(record):
    _register_fonts()
    data = document_data(record)
    stream = BytesIO()
    ink, muted, blue = colors.HexColor("#17243b"), colors.HexColor("#607087"), colors.HexColor("#215bb0")
    styles = {
        "body": ParagraphStyle("body", fontName="Sampling", fontSize=8.5, leading=12, textColor=ink, spaceAfter=5, splitLongWords=True),
        "label": ParagraphStyle("label", fontName="Sampling", fontSize=7.3, leading=10, textColor=muted),
        "title": ParagraphStyle("title", fontName="Sampling-Bold", fontSize=22, leading=27, textColor=ink, spaceAfter=6),
        "section": ParagraphStyle("section", fontName="Sampling-Bold", fontSize=11, leading=15, textColor=blue, spaceBefore=15, spaceAfter=9, keepWithNext=True),
        "sub": ParagraphStyle("sub", fontName="Sampling-Bold", fontSize=8, leading=11, textColor=ink, spaceBefore=6, spaceAfter=4),
        "small": ParagraphStyle("small", fontName="Sampling", fontSize=7, leading=10, textColor=muted),
    }

    def p(value, style="body"):
        # Escape all user text; never interpret markup or links from stored fields.
        text = escape(str(value if value is not None else "-")).replace("\r\n", "\n").replace("\n", "<br/>")
        return Paragraph(text, styles[style])

    width = 178 * mm
    story = [
        p("FACTORYOS / MUSTERUNG", "small"), Spacer(1, 4 * mm),
        p("Musterungsauftrag", "title"),
        p(data["number"]), p(data["reason"], "sub"),
        p(("BEARBEITUNGSSTAND - " if data["preliminary"] else "") + data["status"]),
        p(f"Auftragsstand: Version {data['version']}  /  Ausgabe: {data['generated']}", "small"),
        Spacer(1, 2 * mm), p(data["notice"], "small"),
    ]

    def pairs(rows):
        cells = []
        for index in range(0, len(rows), 2):
            row = []
            for label, value in rows[index:index + 2]:
                row.append([p(label, "label"), p(value)])
            if len(row) == 1:
                row.append("")
            cells.append(row)
        table = Table(cells, colWidths=[width / 2] * 2, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fa")),
            ("BOX", (0, 0), (-1, -1), .4, colors.HexColor("#dfe5ed")),
            ("INNERGRID", (0, 0), (-1, -1), .4, colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    for group in data["groups"]:
        story.append(p(group["title"], "section"))
        if group["rows"]:
            story.append(pairs(group["rows"]))
        for label, value in group["texts"]:
            story.extend([CondPageBreak(34), p(label, "sub"), p(value)])
    story.append(p("Prüfungen, Freigaben und Dokumentenlenkung", "section"))
    rows = [[p(x, "sub") for x in ("Prüfpunkt", "Status", "Datum", "Bearbeitet von")]]
    for check in data["checks"]:
        rows.append([p(check[key]) for key in ("label", "status", "date", "user")])
    table = LongTable(rows, colWidths=[69 * mm, 47 * mm, 25 * mm, 37 * mm],
                      repeatRows=1, hAlign="LEFT", splitInRow=1)
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0f8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LINEBELOW", (0, 0), (-1, -1), .35, colors.HexColor("#dfe5ed")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    notes = [c for c in data["checks"] if c["note"]]
    if notes:
        story.append(p("Prüfnotizen und Nachweisreferenzen", "section"))
        for check in notes:
            story.extend([CondPageBreak(34), p(check["label"], "sub"), p(check["note"])])
    story.extend([p("Abschluss und weitere Maßnahmen", "section"), pairs(data["closing"])])
    for label, value in data["closing_texts"]:
        story.extend([CondPageBreak(34), p(label, "sub"), p(value)])

    def page_frame(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dfe5ed"))
        canvas.line(16 * mm, 281 * mm, 194 * mm, 281 * mm)
        canvas.setFont("Sampling", 7)
        canvas.setFillColor(muted)
        canvas.drawString(16 * mm, 285 * mm, "FactoryOS / Musterungsauftrag")
        # Keep arbitrary, possibly long order numbers inside the header.
        canvas.drawRightString(194 * mm, 285 * mm, f"ID {record.id} / Version {data['version']}")
        canvas.line(16 * mm, 15 * mm, 194 * mm, 15 * mm)
        canvas.drawString(16 * mm, 10 * mm, "Gespeicherter Auftragsstand / " + data["generated"])
        canvas.drawRightString(194 * mm, 10 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=21 * mm, bottomMargin=21 * mm,
                            title="Musterungsauftrag " + data["number"], author="FactoryOS")
    doc.build(story, onFirstPage=page_frame, onLaterPages=page_frame)
    stream.seek(0)
    return stream

