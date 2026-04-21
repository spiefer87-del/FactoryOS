# factoryos/modules/quality/inspection_plan/services/drawing_pdf_service.py

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader

from io import BytesIO

import os

from flask import current_app

from factoryos.modules.quality.inspection_plan.services.marker_service import render_qm_markers
from ..models import QualityInspectionPlanVersion, QualityInspectionSection
from factoryos.modules.masterdata.articles.models import Article

# ===============================
# Seitenzahlen (wie früher)
# ===============================
class NumberedCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)

        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(page_count)
            super().showPage()

        super().save()

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.drawRightString(
            200 * mm,
            10 * mm,
            f"Seite {self._pageNumber} von {page_count}"
        )


# ===============================
# MAIN PDF GENERATION
# ===============================
def generate_inspection_plan_pdf(version_id):

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    styles = getSampleStyleSheet()

    pdf_dir = os.path.join(current_app.static_folder, "qm_exports")
    os.makedirs(pdf_dir, exist_ok=True)

    filename = f"inspection_plan_{version.id}.pdf"
    pdf_path = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []

    # ===============================
    # HEADER
    # ===============================
    elements.append(
        Paragraph(
            f"Prüfplan Revision {version.revision}",
            styles["Title"]
        )
    )

    elements.append(Spacer(1, 10))

    # ===============================
    # META DATEN (WICHTIG!)
    # ===============================
    tool = version.plan.tool


    tool_no = tool.tool_no if tool else "-"
    article = version.plan.article

    article_no = article.article_no if article else "-"
    article_name = article.article_name if article else "-"

    meta = [
        ["Werkzeug", tool_no],
        ["Artikel", article_name],
        ["Artikelnummer", article_no],
        ["Status", version.status]
    ]

    meta_table = Table(meta, colWidths=[5*cm, 10*cm])

    meta_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke)
    ]))

    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # ===============================
    # SECTIONS
    # ===============================
    for i, section in enumerate(version.sections):

        elements.extend(build_section(section))

        # kein PageBreak nach letzter Section
        if i < len(version.sections) - 1:
            elements.append(PageBreak())

    # ===============================
    # BUILD PDF
    # ===============================
    doc.build(elements, canvasmaker=NumberedCanvas)

    return f"qm_exports/{filename}"


# ===============================
# SECTION BUILDER
# ===============================
def build_section(section):

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(section.title, styles["Heading2"])
    )

    elements.append(Spacer(1, 10))

    if section.section_type == "dimension":
        elements.extend(build_dimension_section(section))

    if section.section_type == "gauge":
        elements.extend(build_gauge_section(section))

    return elements


# ===============================
# DIMENSION SECTION (MIT MARKERN)
# ===============================
# ==========================================================
# FIX FÜR DEINEN PDF SERVICE
# Nur build_dimension_section austauschen
# ==========================================================

def build_dimension_section(section):

    elements = []
    block = []

    # ======================================================
    # ZEICHNUNG + FINAL MARKER ENGINE
    # ======================================================
    if section.drawing_path:

        img_path = os.path.join(
            current_app.static_folder,
            section.drawing_path
        )

        if os.path.exists(img_path):

            # ----------------------------------------------
            # DB OBJECTS -> MARKER LISTE UMWANDELN
            # ----------------------------------------------
            markers = []

            for c in section.characteristics:
                if c.pos_x is not None and c.pos_y is not None:

                    markers.append({
                        "x": float(c.pos_x),
                        "y": float(c.pos_y),
                        "number": int(c.sort_order)
                    })

            # ----------------------------------------------
            # FINAL RENDER ENGINE
            # ----------------------------------------------
            img = render_qm_markers(
                img_path,
                markers,
                1600
            )


            # ----------------------------------------------
            # EXAKTES SEITENVERHÄLTNIS
            # ----------------------------------------------
            if section.image_width and section.image_height:
                ratio = section.image_height / section.image_width
            else:
                ratio = 1

            target_width = 16 * cm

            img.drawWidth = target_width
            img.drawHeight = target_width * ratio

            block.append(img)
            block.append(Spacer(1, 10))

    # ======================================================
    # TABELLE
    # ======================================================
    if section.characteristics:

        data = [
            ["Nr", "Merkmal", "Soll", "Tol -", "Tol +", "Einheit"]
        ]

        for c in section.characteristics:

            data.append([
                c.sort_order,
                c.name or "",
                c.target_value or "",
                c.tolerance_minus or "",
                c.tolerance_plus or "",
                c.unit or ""
            ])

        table = Table(
            data,
            colWidths=[1.2*cm, 6*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm]
        )

        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("ALIGN", (2,1), (-1,-1), "CENTER"),
        ]))

        block.append(table)

    # ======================================================
    # KEEP TOGETHER
    # ======================================================
    if block:
        elements.append(KeepTogether(block))

    return elements

# ===============================
# GAUGE SECTION
# ===============================
def build_gauge_section(section):

    elements = []

    data = [
        ["Nr", "Merkmal", "Messmittel", "Methode"]
    ]

    for g in section.gauge_checks:

        gauge_name = ""

        if g.gauge:
            gauge_name = f"{g.gauge.gauge_no} - {g.gauge.name}"

        data.append([
            g.sort_order,
            g.name,
            gauge_name,
            g.method
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elements.append(table)

    return elements




def export_section_drawing_pdf(section_id):

    img = render_qm_markers(
        image_path=image_path,
        markers=markers
    )

    page_w = img.drawWidth
    page_h = img.drawHeight

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    # DIREKT DAS BILDOBJEKT VERWENDEN
    reader = ImageReader(img._imgdata)

    c.drawImage(
        reader,
        0,
        0,
        width=page_w,
        height=page_h,
        mask='auto'
    )

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
