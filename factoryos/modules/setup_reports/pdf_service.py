from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, PageBreak, Paragraph, Spacer, LongTable, TableStyle, KeepTogether
from factoryos.modules.sampling.pdf_service import _register_fonts
from .schema import FIELDS, PROFILES, STEPS, ORIGINS
from .service import gaps
from werkzeug.utils import secure_filename


def tool_number(report):
    return str(report.context.get('tool_no') or report.tool.tool_no or f'Werkzeug_{report.tool_id}')


def download_name(report):
    # Never allow path separators, control characters or header injection in downloads.
    prefix=secure_filename(tool_number(report))[:100].strip('._') or f'Werkzeug_{report.tool_id}'
    return f'{prefix}_Einstellbericht_{report.id}_Stand_{report.version}.pdf'


def build_pdf(report):
    _register_fonts();stream=BytesIO();width=178*mm
    body=ParagraphStyle("SetupBody",fontName="Sampling",fontSize=8,leading=11,textColor=colors.HexColor("#20334d"),splitLongWords=True)
    heading=ParagraphStyle("SetupHeading",parent=body,fontName="Sampling-Bold",fontSize=12,leading=16,spaceBefore=14,spaceAfter=8,keepWithNext=True)
    title=ParagraphStyle("SetupTitle",parent=heading,fontSize=22,leading=27)
    def p(text,style=body):return Paragraph(escape(str(text or "-")).replace("\n","<br/>"),style)
    status={"open":"Offen","confirmed":"Bestätigt","na":"Nicht zutreffend"}
    def table(rows,widths):
        t=LongTable([[p(cell) for cell in row] for row in rows],colWidths=widths,repeatRows=1,hAlign="LEFT",splitInRow=1)
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eaf1fa")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f7f9fc")]),("LINEBELOW",(0,0),(-1,-1),.3,colors.HexColor("#dbe4ef")),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        return t
    data=report.data;missing=gaps(report)
    state_label=('GESPEICHERTER ABSCHLUSS - '+str(len(missing))+' Prüfpunkte' if missing else 'GEPRÜFT ABGESCHLOSSEN') if report.state=='released' else f'ENTWURF - {len(missing)} offene Prüfpunkte'
    story=[NextPageTemplate('detail'),Spacer(1,1),PageBreak(),p("FACTORYOS / ANLAGE ZUM FB-18"),p("Vollständige Angaben",title),
        p(f"Werkzeug {report.context.get('tool_no','-')} | Maschine {report.context.get('machine_no') or 'offen'} | Artikel {report.context.get('article_no') or 'offen'}"),
        p(f"Bericht {report.id} / Stand {report.version} / "+state_label),
        p("Dokumentation, keine Maschinen- oder Sicherheitsfreigabe. Materialvorgaben sind erst nach Bestätigung verwendete Einstellungen. Soll- und Messwerte getrennt beachten."),Spacer(1,4*mm)]
    for step,label in STEPS:
        if step=="review":continue
        story.append(p(label,heading));rows=[["Parameter","Wert / Einheit","Prüfstatus","Herkunft / Hinweis"]]
        for key,spec in FIELDS.items():
            if spec["step"]!=step:continue
            item=data.get("values",{}).get(key,{})
            source=ORIGINS.get(item.get("origin"),"Handeingabe")
            if item.get("photo_id"):source+=" / Foto #"+str(item["photo_id"])
            if item.get("reason"):source+="\n"+item["reason"]
            display=(item.get("value")+" "+item.get("unit",spec["unit"])) if item.get("value") else ("-" if item.get("status")=="na" else "Offen")
            rows.append([spec["label"],display,status.get(item.get("status"),"Offen"),source])
        story.append(table(rows,[width*.28,width*.26,width*.15,width*.31]))
        for key,spec in PROFILES.items():
            if spec["step"]!=step:continue
            item=data.get("profiles",{}).get(key,{})
            if not item.get('rows'):
                parts=[p(spec['label']+' - '+status.get(item.get('status'),'Offen'),heading)]
                if item.get('reason'):parts.append(p(item['reason']))
                if item.get('status')!='na':parts.append(p('Noch nicht erfasst'))
                story.append(KeepTogether(parts));continue
            story.append(p(spec["label"]+" - "+status.get(item.get("status"),"Offen"),heading))
            if item.get("reason"):story.append(p(item["reason"]))
            if item.get("photo_id"):story.append(p("Quelle: Foto #"+str(item["photo_id"])))
            rows=[["Stufe / Zone","Aktiv"]+[column[1] for column in spec["columns"]]]
            for row in item["rows"]:
                cells=[row["label"],{"yes":"Ja","no":"Nein","unknown":"Offen"}.get(row["active"],"Offen")]
                for column,_,unit in spec["columns"]:
                    cell=row["values"].get(column,{})
                    cells.append((cell['value']+' '+cell.get('unit',unit)) if cell.get('value') else '-')
                rows.append(cells)
            story.append(table(rows,[width/len(rows[0])]*len(rows[0])))
    story.append(p("Dokumentationsstand",heading))
    story.append(p(f"Erstellt: {report.created_at:%d.%m.%Y %H:%M} UTC / Benutzer-ID {report.created_by_id}"))
    if report.released_at:story.append(p(f"Geprüft abgeschlossen: {report.released_at:%d.%m.%Y %H:%M} UTC / Benutzer-ID {report.released_by_id}"))
    if missing:
        story.append(p("Noch offene Angaben",heading))
        story.append(p("; ".join(g["label"] for g in missing)))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont("Sampling",7);canvas.setFillColor(colors.HexColor("#607087"))
        canvas.drawString(16*mm,12*mm,f"FactoryOS | Einstellbericht {report.id} | Stand {report.version}")
        canvas.drawRightString(194*mm,12*mm,f"Seite {doc.page}");canvas.restoreState()
    from .fb18_cover import draw_cover
    doc=BaseDocTemplate(stream,pagesize=A4,title=f'{tool_number(report)} – Einstellbericht {report.id} / Stand {report.version}')
    doc.addPageTemplates([
        PageTemplate(id='cover',pagesize=landscape(A4),frames=[Frame(8*mm,16*mm,281*mm,176*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=lambda canvas,doc:draw_cover(canvas,report)),
        PageTemplate(id='detail',pagesize=A4,frames=[Frame(16*mm,20*mm,178*mm,262*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=footer),
    ])
    doc.build(story)
    return stream.getvalue()
