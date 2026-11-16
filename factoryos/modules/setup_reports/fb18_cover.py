"""Landscape FB-18 layout; full, unshortened values remain in the appendix."""
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph,Table,TableStyle,Spacer
from .schema import FIELDS
from .service import gaps
from .screen_numbers import safe_scalar


def draw_cover(canvas,report):
    page_w,page_h=landscape(A4);margin=8*mm
    values=report.data.get('values',{});profiles=report.data.get('profiles',{})
    regular=ParagraphStyle('FB18',fontName='Sampling',fontSize=7.1,leading=8.4,textColor=colors.black)
    bold=ParagraphStyle('FB18Bold',parent=regular,fontName='Sampling-Bold')
    def short(text,limit=46):
        text=' '.join(str(text or '').split())
        return text if len(text)<=limit else text[:limit-3]+'...'
    def p(value,header=False):return Paragraph(escape(str(value or '-')),bold if header else regular)
    def fit(text,width):
        text=str(text or '-')
        if stringWidth(text,'Sampling',regular.fontSize)<=width:return text
        while text and stringWidth(text+'...','Sampling',regular.fontSize)>width:text=text[:-1]
        return text+'...'
    def value(key,limit=46):
        item=values.get(key,{})
        if item.get('status')=='na':return 'n.z.'
        raw=item.get('value','')
        if key=='dosing_position' and item.get('origin')=='photo' and not safe_scalar(key,raw):return '* OCR-Wert prüfen'
        display=(str(raw)+' '+item.get('unit',FIELDS[key]['unit'])).strip() if raw else 'offen'
        if item.get('status')!='confirmed':display='* '+display
        return short(display,limit)
    def grid(rows,width,ratio=.50):
        converted=[];spans=[];full_rows=[]
        for index,row in enumerate(rows):
            if isinstance(row,str):converted.append([p(row,True),'']);spans.append(index)
            elif row[0] is None:converted.append([row[1],'']);full_rows.append(index)
            else:converted.append([p(row[0]),row[1] if isinstance(row[1],(Table,Paragraph)) else p(fit(row[1],width*(1-ratio)-6))])
        table=Table(converted,colWidths=[width*ratio,width*(1-ratio)],hAlign='LEFT')
        style=[('GRID',(0,0),(-1,-1),.45,colors.HexColor('#333333')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),('TOPPADDING',(0,0),(-1,-1),1.6),('BOTTOMPADDING',(0,0),(-1,-1),1.6)]
        for row in spans:style.extend([('SPAN',(0,row),(1,row)),('BACKGROUND',(0,row),(1,row),colors.HexColor('#e8e8e8'))])
        for row in full_rows:style.append(('SPAN',(0,row),(1,row)))
        table.setStyle(TableStyle(style));return table
    def row(label,key,limit=46):return(label,value(key,limit))
    left_width=95*mm;middle_width=76*mm;right_width=110*mm
    left=grid([
        row('Kunde','customer'),row('Artikel','article_name'),row('Artikel-Nr.','article_no'),
        row('Fachzahl','cavities'),row('Angusssystem','gate_system'),row('Schussgewicht','shot_weight'),
        row('Teilegewicht','part_weight'),row('Schuss ohne Anguss','shot_without_runner'),row('Angussgewicht','runner_weight'),
        row('Materialverbrauch','material_consumption'),'Maschinen- und Werkzeugdaten',
        row('Werkzeug-Nr.','tool_no'),row('Lagerort','tool_location'),row('Maschinen-Nr.','machine_no'),
        row('Maschinen-Typ','machine_name'),row('Steuerung','controller'),row('Schließkraft','clamping_force'),
        row('Zyl.-Durchmesser','screw_diameter'),row('Düsenradius','nozzle_radius'),row('Einbauhöhe','mold_height'),
    ],left_width,.48)
    middle=grid([
        'Werkstoff',row('Hersteller','manufacturer',35),row('Werkstoffgruppe','polymer',35),row('Handelsname','material_name',35),
        row('Material-Nr.','material_no',35),row('Farbe','color',35),row('MB-Anteil','batch_percent',35),
        row('MB-Nr.','batch_no',35),row('Farbbatch','batch_name',35),row('Farbton / RAL','batch_color',35),
        'Trocknung',row('Temperatur','drying_temperature',35),row('Trocknungszeit','drying_time',35),
        'Werkzeug-Kühlung',row('Düsenseite','nozzle_cooling',35),row('Auswerferseite','ejector_cooling',35),
        row('Kerne','core_cooling',35),row('Schieber','slide_cooling',35),row('Temperiergeräte','temperature_devices',35),
        row('Musterung-Nr.','sampling_no',35),row('Heißkanal-Regler','hotrunner_controller',35),
    ],middle_width,.49)
    def profile_summary(key,column,limit=85):
        item=profiles.get(key,{})
        if item.get('status')=='na':return 'n.z.'
        parts=[];units=[]
        for r in item.get('rows',[])[:4]:
            cell=r.get('values',{}).get(column,{})
            flag='aus' if r.get('active')=='no' else '?' if r.get('active')!='yes' else ''
            parts.append((flag+' '+str(cell.get('value') or '-')).strip());units.append(cell.get('unit',''))
        if len(set(units))>1:parts=[part+' '+unit for part,unit in zip(parts,units)]
        result=' / '.join(parts) or 'offen'
        if units and len(set(units))==1:result+=' '+units[0]
        if len(item.get('rows',[]))>4:result+=' / weiter: Anlage'
        if item.get('status')!='confirmed':result='* '+result
        return short(result,limit)
    cylinder=profiles.get('cylinder',{});zone_rows=cylinder.get('rows',[])[:8]
    if zone_rows:
        header=['Zone']+[short(r.get('label','?'),10) for r in zone_rows]
        settings=['Soll °C']+[(('aus ' if r.get('active')=='no' else '? ' if r.get('active')!='yes' else '')+str(r.get('values',{}).get('set',{}).get('value') or '-')) for r in zone_rows]
        temperatures=Table([[p(c) for c in header],[p(c) for c in settings]],colWidths=[(right_width-6)/(len(zone_rows)+1)]*(len(zone_rows)+1))
        temperatures.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.black),('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    else:temperatures=p('n.z.' if cylinder.get('status')=='na' else '* Zonen noch nicht erfasst')
    right_rows=[('Zeichnung / Index',value('drawing_no',24)+' / '+value('drawing_revision',12)),row('Betriebsart','mode'),row('Düse abfahren','nozzle_return'),
        'Zylindertemperatur °C (Soll)',(None,temperatures),'Zeiten (Sekunden)',
        row('Spritzzeit (Ist)','injection_time'),row('Restkühlzeit','cooling_time'),row('Pausenzeit','pause_time'),
        row('Soll-Zykluszeit','cycle_target'),row('Dosierzeit (Ist)','dosing_time'),row('Dosierverzögerung','dosing_delay'),
        row('EE zurück verzögert','unit_return_delay'),'Drücke / Nachdruckprofil',
        row('Spritzdruck (Soll)','injection_pressure'),row('Spitzenwert pmax (Ist)','peak_pressure'),row('Umschaltdruck (Ist)','switch_pressure'),
        row('Staudruck','back_pressure'),('Nachdruck (Druck)',profile_summary('holding_profile','pressure')),('Nachdruck (Zeit)',profile_summary('holding_profile','time')),
        'Wege / Geschwindigkeiten',('Einspritzgeschw.',profile_summary('injection_profile','speed')),('Einspritzpositionen',profile_summary('injection_profile','position')),
        row('Nachdruckgeschw.','holding_speed'),row('Plastifizierweg','dosing_position'),row('Dekompression','decompression'),row('Umschaltpunkt','switch_position'),
        row('Massepolster (Ist)','cushion'),row('Schnecken-Drehzahl','screw_speed'),'Auswerfer / Entnahme',
        row('Auswerferhübe','ejector_strokes'),row('Entnahmegerät','handling'),row('Roboter-Kopf Nr.','robot_head')]
    right=grid(right_rows,right_width,.49)
    top=page_h-18*mm
    def draw(table,x,y,width):
        _,height=table.wrap(width,page_h)
        if height>page_h-32*mm:raise ValueError('FB-18-Deckblatt passt nicht auf die Seite. Bitte Layout prüfen.')
        table.drawOn(canvas,x,y-height);return height
    canvas.saveState();canvas.setFont('Sampling-Bold',12)
    canvas.drawString(margin,page_h-8*mm,'FB-18  Einstellbericht')
    canvas.setFont('Sampling',8)
    missing=gaps(report)
    state=('GESPEICHERTER ABSCHLUSS - '+str(len(missing))+' Prüfpunkte' if missing else 'GEPRÜFT ABGESCHLOSSEN') if report.state=='released' else f'ENTWURF - {len(missing)} offene Prüfpunkte'
    canvas.drawRightString(page_w-margin,page_h-8*mm,f'Bericht {report.id} / Stand {report.version} / {state}')
    left_h=draw(left,margin,top,left_width);middle_h=draw(middle,margin+left_width,top,middle_width)
    right_h=draw(right,margin+left_width+middle_width,top,right_width)
    notes=' | '.join(filter(None,[values.get(k,{}).get('value','') for k in ('notes','mold_safety','core_sequence')]))
    bottom=top-max(left_h,middle_h)
    left_combined=left_width+middle_width
    rows=['Bemerkung / Ablauf',(None,p(short(notes,600) or '-')),('Verpackung',value('packaging',190)),
          ('Datum / Name',value('record_date',20)+' / '+value('operator',65)),
          ('Geändert am (UTC)',report.updated_at.strftime('%d.%m.%Y %H:%M'))]
    note_table=grid(rows,left_combined,.20)
    _,note_h=note_table.wrap(left_combined,page_h)
    line_height=regular.leading+3.2
    empty_lines=max(0,int((right_h-max(left_h,middle_h)-note_h)/line_height))
    if empty_lines:
        rows[2:2]=[(None,Spacer(1,regular.leading)) for _ in range(empty_lines)]
        note_table=grid(rows,left_combined,.20);_,note_h=note_table.wrap(left_combined,page_h)
    if bottom-note_h<17*mm:raise ValueError('FB-18-Bemerkungen überschreiten das Deckblatt.')
    note_table.drawOn(canvas,margin,bottom-note_h)
    canvas.setFont('Sampling',6.8)
    canvas.drawString(margin,11*mm,'* ungeprüft / offen; n.z. = nicht zutreffend. Gekürzte Texte, vollständige Profile, Quellen und Prüfstatus: siehe Anlage.')
    canvas.drawString(margin,7*mm,'FactoryOS / FB-18-Aufbau. Dokumentation, keine Maschinen- oder Sicherheitsfreigabe. Temperaturen: Soll, keine Ist-Ersatzwerte.')
    canvas.drawRightString(page_w-margin,7*mm,'Seite 1')
    canvas.restoreState()
