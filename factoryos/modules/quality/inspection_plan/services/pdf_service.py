"""Complete, wrapped inspection instructions. No measurement result is invented."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from flask import current_app, send_file, abort
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from ..models import QualityInspectionPlanVersion, QualityInspectionSection
from ..definitions import STATUS_LABELS
from .marker_service import render_qm_markers


def paragraph(value,style):
    return Paragraph(escape(str(value if value is not None else '-')).replace('\n','<br/>'),style)


def table(rows,widths,styles):
    content=[[paragraph(value,styles['Small']) for value in row] for row in rows]
    item=Table(content,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT',splitInRow=1)
    item.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8eef7')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#cbd5e1')),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return item


def media_path(relative):
    root=Path(current_app.static_folder).resolve()
    path=(root/(relative or '')).resolve()
    if not path.is_relative_to(root) or not path.is_file():return None
    return path


def fit_image(source):
    image=Image(source)
    scale=min(170*mm/image.imageWidth,135*mm/image.imageHeight)
    image.drawWidth=image.imageWidth*scale;image.drawHeight=image.imageHeight*scale
    image.hAlign='LEFT'
    return image


def generate_inspection_plan_pdf(version_id):
    version=QualityInspectionPlanVersion.query.get_or_404(version_id)
    styles=getSampleStyleSheet()
    regular=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    bold=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    font='Helvetica';bold_font='Helvetica-Bold'
    if regular.is_file() and bold.is_file():
        if 'QMDejaVu' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('QMDejaVu',str(regular)))
            pdfmetrics.registerFont(TTFont('QMDejaVuBold',str(bold)))
        font='QMDejaVu';bold_font='QMDejaVuBold'
    for name in ('Normal','BodyText','Title','Heading1','Heading2','Heading3'):
        styles[name].fontName=bold_font if name in ('Title','Heading1','Heading2','Heading3') else font
    styles.add(ParagraphStyle(name='Small',fontName=font,fontSize=9,leading=13,splitLongWords=True))
    output=BytesIO()
    doc=SimpleDocTemplate(output,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=18*mm,bottomMargin=19*mm,
        title=f'Prüfplan {version.plan.tool.tool_no} Revision {version.revision}')
    body=[paragraph(f'Prüfplan · {version.plan.tool.tool_no}',styles['Title']),paragraph(f'Revision {version.revision} · {STATUS_LABELS.get(version.status,version.status)}',styles['Heading2'])]
    if version.status!='released':body.append(paragraph('Keine aktuell freigegebene Arbeitsfassung. Status beachten.',styles['Normal']))
    body.append(table([['Werkzeug / Artikel','Zuordnung'],['Werkzeug',version.plan.tool.tool_no],
        ['Artikelnummer',version.plan.article.article_no],['Bezeichnung',version.plan.article.article_name],
        ['Freigabe',version.released_at.strftime('%d.%m.%Y %H:%M UTC') if version.released_at else 'Noch nicht freigegeben'],
        ['Freigegeben durch',version.released_by.username if version.released_by else '-']], [45,125],styles))
    body.append(Spacer(1,12))
    body.append(paragraph('Prüfanweisung: Dieser Plan legt Kriterien und Prüfumfang fest; er ist kein ausgefülltes Messprotokoll.',styles['Normal']))
    for index,section in enumerate(version.sections,1):
        body.append(PageBreak())
        body.append(paragraph(f'{index}. {section.title}',styles['Heading1']))
        settings=section.inspection_settings or {}
        body.append(table([['Prüfumfang','Vorgabe'],['Intervall / Anlass',settings.get('frequency','Nicht angegeben')],
            ['Stichprobenumfang',settings.get('sample_size','Nicht angegeben')],['Verantwortung',settings.get('responsible','Nicht angegeben')]], [45,125],styles))
        if settings.get('instructions'):
            body.extend([Spacer(1,10),paragraph(settings['instructions'],styles['Normal'])])
        body.append(Spacer(1,12))
        if section.section_type=='dimension':
            path=media_path(section.drawing_path)
            if path:
                markers=[dict(x=c.pos_x,y=c.pos_y,number=c.sort_order,rotation=c.rotation or 0) for c in section.characteristics if c.pos_x is not None and c.pos_y is not None]
                body.extend([fit_image(render_qm_markers(str(path),markers,170,135)),Spacer(1,12)])
            elif section.drawing_path:body.append(paragraph('Hinterlegte Zeichnungsdatei fehlt.',styles['Normal']))
            body.append(table([['Nr.','Prüfmerkmal','Soll','Tol. -','Tol. +','Einheit']]+[[c.sort_order,c.name,c.target_value,c.tolerance_minus,c.tolerance_plus,c.unit] for c in section.characteristics],[10,65,25,25,25,20],styles))
            for snippet in section.snippets:
                path=media_path(snippet.image_path)
                if path:body.extend([Spacer(1,12),fit_image(str(path)),paragraph(snippet.description or '',styles['Normal'])])
        elif section.section_type=='gauge':
            body.append(table([['Nr.','Prüfmerkmal','Prüfmittel','Methode / Kriterium']]+[[c.sort_order,c.name,
                f'{c.gauge.gauge_no} · {c.gauge.name}' if c.gauge else 'Nicht zugeordnet',c.method] for c in section.gauge_checks],[10,45,50,65],styles))
        else:
            for check in section.checks:
                body.append(paragraph(f'{check.sort_order}. {check.name}',styles['Heading3']))
                body.append(table([['Prüfvorgabe','Inhalt'],['Annahme- / Fehlerkriterium',check.requirement],['Prüfmethode / Hilfsmittel',check.method]]+
                    ([['Sollgewicht',f'{check.target_value} {check.unit}'],['Toleranz',f'-{check.tolerance_minus} / +{check.tolerance_plus} {check.unit}']] if section.section_type=='weight' else []),[45,125],styles))
                body.append(Spacer(1,10))
            if not section.checks:body.append(paragraph('Noch keine Prüfmerkmale erfasst.',styles['Normal']))
            for reference in section.images:
                path=media_path(reference.image_path)
                if path:body.extend([Spacer(1,10),fit_image(str(path)),paragraph(reference.description or 'Referenzbild',styles['Normal'])])
                else:body.append(paragraph('Referenzbild fehlt: '+(reference.description or reference.image_path),styles['Normal']))
    def footer(canvas,document):
        canvas.saveState();canvas.setFont(font,8)
        canvas.drawString(20*mm,10*mm,f'{version.plan.tool.tool_no} | Rev. {version.revision} | {STATUS_LABELS.get(version.status,version.status)}')
        canvas.drawRightString(190*mm,10*mm,f'Seite {document.page}');canvas.restoreState()
    doc.build(body,onFirstPage=footer,onLaterPages=footer)
    output.seek(0);return output


def export_section_drawing(section_id):
    section=QualityInspectionSection.query.get_or_404(section_id)
    path=media_path(section.drawing_path)
    if not path:abort(404,'Keine Zeichnung vorhanden.')
    markers=[dict(x=c.pos_x,y=c.pos_y,number=c.sort_order,rotation=c.rotation or 0) for c in section.characteristics if c.pos_x is not None and c.pos_y is not None]
    output=render_qm_markers(str(path),markers,170,135)
    return send_file(output,mimetype='image/png',as_attachment=True,download_name=f'Zeichnung_{section.id}.png')
