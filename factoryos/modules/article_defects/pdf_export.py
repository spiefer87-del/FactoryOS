"""Private, on-demand A4 reports; escaped text, bounded photos, no public files."""
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
import reportlab
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,KeepTogether,PageBreak

def timestamp(value):
    return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M %Z') if value else '-'

def build_pdf(entries,photo_directory,title='Artikel-Fehlerkatalog'):
    fonts=Path(reportlab.__file__).parent/'fonts'
    if 'FactoryDefect' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('FactoryDefect',str(fonts/'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('FactoryDefectBold',str(fonts/'VeraBd.ttf')))
        pdfmetrics.registerFontFamily('FactoryDefect',normal='FactoryDefect',bold='FactoryDefectBold',italic='FactoryDefect',boldItalic='FactoryDefectBold')
    body=ParagraphStyle('DefectBody',fontName='FactoryDefect',fontSize=9.5,leading=14,textColor=colors.HexColor('#1e293b'),spaceAfter=6,splitLongWords=True)
    heading=ParagraphStyle('DefectHeading',parent=body,fontName='FactoryDefectBold',fontSize=12,leading=17,spaceBefore=10,spaceAfter=6,keepWithNext=True)
    headline=ParagraphStyle('DefectTitle',parent=heading,fontSize=19,leading=25,spaceBefore=0,spaceAfter=10)
    small=ParagraphStyle('DefectSmall',parent=body,fontSize=8,leading=11,textColor=colors.HexColor('#64748b'))
    def p(value,style=body):return Paragraph(escape(str(value or '-')).replace('\n','<br/>'),style)
    result=BytesIO();doc=SimpleDocTemplate(result,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=27*mm,bottomMargin=20*mm,title=title,author='FactoryOS')
    story=[];exported=timestamp(datetime.utcnow())
    for index,entry in enumerate(entries):
        if index:story.append(PageBreak())
        story.extend([p('FEHLERBILD #'+str(entry.id),small),p(entry.title,headline)])
        rows=[['Artikelnummer',entry.article.article_no],['Artikel',entry.article.article_name],['Werkzeugnummer',entry.tool_no or 'Nicht angegeben'],['Fehlerart',entry.defect_type],['Status / Version',('Archiviert' if entry.archived else 'Aktiv')+' / '+str(entry.version)],['Erfasst',timestamp(entry.created_at)+' / '+(entry.author.username if entry.author else '-')],['Zuletzt geändert',timestamp(entry.updated_at)]]
        table=Table([[p(k,small),p(v)] for k,v in rows],colWidths=[42*mm,132*mm],hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f1f5f9')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        story.extend([table,p('Beobachteter Fehler',heading),p(entry.description),p('Erprobte Abhilfe / Hinweise',heading),p(entry.remedy or 'Noch keine Abhilfe dokumentiert.'),p('Fehlerfotos',heading)])
        if not entry.photos:story.append(p('Keine Fotos hinterlegt.',small))
        for number,photo in enumerate(entry.photos,1):
            path=Path(photo_directory)/photo.filename
            try:
                if Path(photo.filename).name!=photo.filename:raise ValueError('Ungültiger Dateiname')
                raw=BytesIO(path.read_bytes())
                with PILImage.open(raw) as image:
                    width,height=image.size
                    if width*height>24_000_000:raise ValueError('Bild zu groß')
                    image.verify()
                raw.seek(0);scale=min(174*mm/width,93*mm/height)
                image=Image(raw,width=width*scale,height=height*scale);image.hAlign='LEFT'
                story.append(KeepTogether([p('Foto '+str(number),small),image,Spacer(1,6*mm)]))
            except (OSError,ValueError,PILImage.DecompressionBombError):story.append(p('Foto '+str(number)+' ist derzeit nicht verfügbar. Bitte Originaleintrag prüfen.',small))
        story.append(p('Dokumentierte Beobachtung und Erfahrungen. Keine automatische Ursachenbewertung oder Maschinenfreigabe.',small))
    if not entries:story=[p(title,headline),p('Für diese Auswahl sind keine Einträge vorhanden.')]
    def frame(canvas,document):
        canvas.saveState();canvas.setFillColor(colors.HexColor('#0f172a'));canvas.rect(0,A4[1]-18*mm,A4[0],18*mm,fill=1,stroke=0)
        canvas.setFillColor(colors.white);canvas.setFont('FactoryDefectBold',13);canvas.drawString(18*mm,A4[1]-12*mm,'FactoryOS')
        canvas.setFont('FactoryDefect',9);canvas.drawRightString(A4[0]-18*mm,A4[1]-12*mm,'Qualität | Fehlerkatalog')
        canvas.setStrokeColor(colors.HexColor('#cbd5e1'));canvas.line(18*mm,15*mm,A4[0]-18*mm,15*mm)
        canvas.setFont('FactoryDefect',7);canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawString(18*mm,10*mm,'Export: '+exported);canvas.drawRightString(A4[0]-18*mm,10*mm,'Seite '+str(document.page));canvas.restoreState()
    doc.build(story,onFirstPage=frame,onLaterPages=frame)
    result.seek(0);return result
