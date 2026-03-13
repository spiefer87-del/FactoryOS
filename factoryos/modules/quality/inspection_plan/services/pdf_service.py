from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak
)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

import os

from flask import current_app

from factoryos.modules.quality.models import (
    QualityInspectionPlanVersion
)


def generate_inspection_plan_pdf(version_id):

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    styles = getSampleStyleSheet()

    pdf_dir = os.path.join(current_app.static_folder, "qm_exports")

    os.makedirs(pdf_dir, exist_ok=True)

    filename = f"inspection_plan_{version.id}.pdf"

    pdf_path = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4
    )

    elements = []

    elements.append(
        Paragraph(
            f"Prüfplan Revision {version.revision}",
            styles["Heading1"]
        )
    )

    elements.append(Spacer(1, 20))

    # -------------------------
    # Module durchlaufen
    # -------------------------

    for section in version.sections:

        elements.extend(
            build_section(section)
        )

        elements.append(PageBreak())

    doc.build(elements)

    return f"qm_exports/{filename}"

def build_section(section):

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(section.title, styles["Heading2"])
    )

    if section.section_type == "dimension":

        elements.extend(
            build_dimension_section(section)
        )

    if section.section_type == "gauge":

        elements.extend(
            build_gauge_section(section)
        )

    return elements

def build_dimension_section(section):

    elements = []

    if section.drawing_path:

        img_path = os.path.join(
            current_app.static_folder,
            section.drawing_path
        )

        elements.append(
            Image(img_path, width=16*cm, height=12*cm)
        )

    table_data = [
        ["#", "Merkmal", "Soll", "-Tol", "+Tol", "Einheit"]
    ]

    for c in section.characteristics:

        table_data.append([
            c.sort_order,
            c.name,
            c.target_value,
            c.tolerance_minus,
            c.tolerance_plus,
            c.unit
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey)
    ]))

    elements.append(table)

    return elements

def build_gauge_section(section):

    elements = []

    table_data = [
        ["#", "Merkmal", "Messmittel", "Methode"]
    ]

    for g in section.gauge_checks:

        gauge_name = ""

        if g.gauge:
            gauge_name = f"{g.gauge.gauge_no} - {g.gauge.name}"

        table_data.append([
            g.sort_order,
            g.name,
            gauge_name,
            g.method
        ])

    table = Table(table_data)

    elements.append(table)

    return elements

