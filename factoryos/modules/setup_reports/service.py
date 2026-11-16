import copy
import json
import math
import re
from datetime import datetime, date
from flask import abort
from flask_login import current_user
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.machines.models import Machine
from factoryos.modules.masterdata.materials.models import Material
from .models import SetupReportRevision, SetupReportPhoto
from .schema import FIELDS, PROFILES, UNITS, profile_defaults
from .screen_numbers import safe_scalar
from .validation import ReportValidationError as Invalid


def entry(value, origin="master", evidence=""):
    return dict(value=str(value), unit="", origin=origin, evidence=evidence,
                status="open", reason="", photo_id=None)


def choices(tool):
    can = lambda name: has_permission(current_user, name+".view")
    return dict(articles=[dict(id=a.id, label=f"{a.article_no} - {a.article_name}") for a in tool.articles] if can("articles") else [],
                machines=[dict(id=m.id, label=f"{m.machine_no} - {m.name or ''}") for m in Machine.query.order_by(Machine.machine_no)] if can("machines") else [],
                materials=[dict(id=m.id, label=f"{m.material_no} - {m.name}", category=m.material_type) for m in Material.query.order_by(Material.material_no)] if can("materials") else [])


def make_context(tool, ids):
    if not isinstance(ids,dict):raise ValueError("Ungültige Stammdaten-Zuordnungen.")
    ids=dict(ids)
    if 'article_id' not in ids and len(tool.articles)==1 and has_permission(current_user,'articles.view'):
        ids['article_id']=tool.articles[0].id
    def selected(model, field, permission):
        raw=ids.get(field)
        if raw in (None, "", 0):return None
        if not has_permission(current_user, permission+".view"):abort(403)
        if isinstance(raw,bool) or not str(raw).isdigit():raise Invalid('Ungültige Stammdaten-ID.',context=field)
        try:obj=db.session.get(model, int(raw))
        except (ValueError, TypeError):raise Invalid("Ungültige Stammdaten-Zuordnung.",context=field)
        if not obj:raise Invalid("Stammdatensatz nicht mehr vorhanden. Bitte neu auswählen.",context=field)
        return obj
    article=selected(Article,"article_id","articles")
    if article and not any(a.id==article.id for a in tool.articles):
        raise Invalid("Artikel ist diesem Werkzeug nicht zugeordnet. Zuordnung bitte in den Artikelstammdaten pflegen.",context="article_id")
    machine=selected(Machine,"machine_id","machines")
    if article:
        if has_permission(current_user,'materials.view'):
            ids.setdefault("material_id", article.material_id)
            ids.setdefault("masterbatch_id", article.masterbatch_id)
    material=selected(Material,"material_id","materials")
    batch=selected(Material,"masterbatch_id","materials")
    if material and material.material_type=="masterbatch":raise Invalid("Hauptrohstoff darf kein Masterbatch sein.",context="material_id")
    if batch and batch.material_type!="masterbatch":raise Invalid("Farbbatch muss zur Kategorie Masterbatch gehören.",context="masterbatch_id")
    context=dict(tool_id=tool.id, tool_no=tool.tool_no, tool_name=tool.name or "",
                 machine_id=machine.id if machine else None, machine_no=machine.machine_no if machine else "",
                 article_id=article.id if article else None, article_no=article.article_no if article else "",
                 material_id=material.id if material else None, material_no=material.material_no if material else "",
                 masterbatch_id=batch.id if batch else None, batch_no=batch.material_no if batch else "")
    values={}
    def put(key,value,origin="master",evidence=""):
        if value is not None and str(value).strip():
            values[key]=entry(value,origin,evidence or "Aktuelle Stammdaten - am konkreten Einstellstand bestätigen")
            values[key]["unit"]=FIELDS[key]["unit"]
    put("tool_no",tool.tool_no);put("tool_name",tool.name);put("tool_location",tool.location);put("cavities",tool.cavities)
    if machine:
        put("machine_no",machine.machine_no);put("machine_name",machine.name or machine.model)
        put("controller",machine.controller_type)
        tech=machine.injection_molding_data
        if tech:put("screw_diameter",tech.screw_diameter_mm);put("nozzle_radius",tech.nozzle_radius_mm)
    if article:
        put("article_no",article.article_no);put("article_name",article.article_name)
        put("drawing_no",article.drawing_no);put("drawing_revision",article.drawing_revision)
        put("shot_weight",article.shot_weight_g);put("cycle_target",article.cycle_time_s)
        if article.customer:put("customer",f"{article.customer.customer_no} - {article.customer.name}")
        if batch and article.masterbatch_id==batch.id:put("batch_percent",article.masterbatch_percent)
    if material:
        put("material_no",material.material_no);put("material_name",material.name);put("manufacturer",material.manufacturer)
        put("polymer",material.polymer_type);put("color"," / ".join(filter(None,[material.color,material.color_no])))
        put("drying_temperature",material.drying_temperature_c,"recommendation","Materialvorgabe - tatsächlich verwendete Trocknung bestätigen, kein Durchführungsnachweis")
        put("drying_time",material.drying_time_h,"recommendation","Materialvorgabe - tatsächlich verwendete Trocknungsdauer bestätigen")
    if batch:
        put("batch_no",batch.material_no);put("batch_name",batch.name)
        put("batch_color"," / ".join(filter(None,[batch.color,batch.color_no,batch.ral_color])))
    return context,values


def initial_data(values):
    data=dict(values=values, profiles=profile_defaults(), context_confirmed=False)
    data["values"].setdefault("record_date",entry(date.today().isoformat(),"manual","Vorgeschlagenes Tagesdatum - prüfen"))
    data["values"].setdefault("operator",entry(current_user.username,"manual","Angemeldeter Benutzer - Einrichter bestätigen"))
    return data


def numeric(value, **location):
    raw=str(value).strip().replace(",", ".")
    # Standard notation R40/R 40 belongs only to the nozzle-radius field.
    if location.get("field")=="nozzle_radius" and re.fullmatch(r"[Rr]\s*\d+(?:\.\d+)?",raw):
        raw=re.sub(r"^[Rr]\s*","",raw)
    if not raw:return ""
    try:number=float(raw)
    except ValueError:
        message="Eine einzelne Zahl ohne Einheit eingeben (z. B. 40 oder 40,5)."
        if location.get('field')=='nozzle_radius':message="Düsenradius als einzelne Zahl eingeben, z. B. 40, 40,5 oder R40."
        elif location.get('profile'):message+=" Mehrere Werte bitte auf einzelne Profilstufen verteilen."
        raise Invalid(message,**location)
    if not math.isfinite(number) or abs(number)>1e9:raise Invalid("Ungültiger oder zu großer Zahlenwert.",**location)
    return raw


def clean_data(report, payload, suggestions):
    if not isinstance(payload,dict) or len(json.dumps(payload))>180000:raise ValueError("Berichtsdaten fehlen oder sind zu groß.")
    if not isinstance(payload.get('values',{}),dict) or not isinstance(payload.get('profiles',{}),dict):raise ValueError('Ungültige Parameterdaten.')
    old=report.data or {};result=dict(values={},profiles={},context_confirmed=payload.get("context_confirmed") is True)
    photos={p.id:p for p in SetupReportPhoto.query.filter_by(report_id=report.id)}
    def clean_status(item,**location):
        status=item.get("status","open")
        if status not in ("open","confirmed","na"):raise Invalid("Unbekannter Prüfstatus.",**location)
        reason=str(item.get("reason","")).strip()
        if len(reason)>800:raise Invalid("Begründung zu lang (maximal 800 Zeichen).",column="reason",**location)
        if status=="na" and not reason:raise Invalid("Nicht zutreffend benötigt eine Begründung.",column="reason",**location)
        return status,reason
    for key,spec in FIELDS.items():
        item=payload.get("values",{}).get(key,{})
        if not isinstance(item,dict):raise Invalid("Ungültiges Parameterfeld.",field=key)
        value=str(item.get("value","")).strip()
        if len(value)>(4000 if key in ("notes","packaging","mold_safety","core_sequence") else 300):raise Invalid("Text zu lang.",field=key)
        if spec["kind"]=="number":value=numeric(value,field=key)
        if key=="record_date" and value:
            try:date.fromisoformat(value)
            except ValueError:raise Invalid("Einstelldatum muss JJJJ-MM-TT entsprechen.",field=key)
        unit=item.get("unit",spec["unit"])
        if unit not in UNITS.get(spec["unit"],[spec["unit"]]):raise Invalid("Unzulässige Einheit.",field=key)
        status,reason=clean_status(item,field=key)
        if status=="confirmed" and not value:raise Invalid("Leerer Wert kann nicht bestätigt werden.",field=key)
        if key=="cycle_target" and value and float(value)<=0:raise Invalid("Soll-Zykluszeit muss größer null sein.",field=key)
        if key in ('cavities','ejector_strokes','temperature_devices') and value and (not float(value).is_integer() or float(value)<0):
            raise Invalid('Eine nicht negative ganze Anzahl eingeben.',field=key)
        if key=='batch_percent' and value and not 0<=float(value)<=100:raise Invalid('Farbbatch-Anteil muss zwischen 0 und 100 Prozent liegen.',field=key)
        previous=old.get("values",{}).get(key,{})
        source=entry(value,"manual","Bewusste Handeingabe / Korrektur")
        if value==previous.get("value") and unit==previous.get("unit",spec["unit"]):source=copy.deepcopy(previous)
        elif key in suggestions and value==suggestions[key]["value"] and unit==spec["unit"] and item.get("origin") in ("master","recommendation"):
            source=copy.deepcopy(suggestions[key])
        photo=photos.get(item.get("photo_id")) if isinstance(item.get("photo_id"),int) else None
        if photo and any(p.get("field")==key and p.get("value")==value and p.get("unit")==unit for p in photo.result.get("proposals",[])):
            if not safe_scalar(key,value):
                raise Invalid('unsicherer Foto-Wert. Bitte am Bildschirm prüfen und von Hand korrigieren oder entfernen.',field=key)
            provider="extern mit Groq" if photo.result.get("provider")=="groq" else "lokal"
            source=entry(value,"photo","Foto #"+str(photo.id)+" - "+provider+" erkannt; Prüfstatus separat beachten");source["photo_id"]=photo.id
        source.update(value=value,unit=unit,status=status,reason=reason)
        result["values"][key]=source
    for key,spec in PROFILES.items():
        item=payload.get("profiles",{}).get(key,{})
        if not isinstance(item,dict):raise Invalid("Ungültiges Profil.",profile=key)
        status,reason=clean_status(item,profile=key)
        rows=item.get("rows",[])
        if not isinstance(rows,list) or len(rows)>32:raise Invalid("Maximal 32 Stufen / Zonen je Profil.",profile=key)
        columns={c[0]:c for c in spec["columns"]};clean_rows=[]
        for index,row in enumerate(rows):
            if not isinstance(row,dict):raise Invalid("Ungültige Profilzeile.",profile=key,row=index)
            clean=dict(label=str(row.get("label","")).strip()[:100],active=row.get("active","unknown"),values={})
            if clean["active"] not in ("yes","no","unknown"):raise Invalid("Aktivierung der Stufe prüfen.",profile=key,row=index,column="active")
            for column,(_,label,default_unit) in columns.items():
                if not isinstance(row.get('values',{}),dict):raise Invalid('Ungültige Profilwerte.',profile=key,row=index)
                cell=row.get("values",{}).get(column,{})
                if not isinstance(cell,dict):raise Invalid("Ungültige Profilzelle.",profile=key,row=index,column=column)
                unit=cell.get("unit",default_unit)
                if unit not in UNITS.get(default_unit,[default_unit]):raise Invalid("Profileinheit ist ungültig.",profile=key,row=index,column=column)
                val=str(cell.get("value","")).strip()
                if len(val)>500:raise Invalid("Profilangabe ist zu lang.",profile=key,row=index,column=column)
                if default_unit:val=numeric(val,profile=key,row=index,column=column)
                clean["values"][column]=dict(value=val,unit=unit)
            clean_rows.append(clean)
        if status=="confirmed":
            if not clean_rows:raise Invalid("Vor dem Bestätigen mindestens eine Stufe / Zone erfassen.",profile=key)
            for index,row in enumerate(clean_rows):
                if not row['label']:raise Invalid("Stufe / Zone benennen.",profile=key,row=index,column="label")
                if row['active']=='unknown':raise Invalid("Aktivierung ausdrücklich prüfen und Ja oder Nein wählen.",profile=key,row=index,column="active")
                if row['active']=='yes' and not any(c['value'] for c in row['values'].values()):raise Invalid("Für die aktive Stufe mindestens einen Wert erfassen.",profile=key,row=index)
                if key in ('cylinder','hotrunner') and row['active']=='yes' and not row['values']['set']['value']:
                    raise Invalid("Aktive Temperaturzone benötigt einen Sollwert. Istwert ersetzt keinen Sollwert.",profile=key,row=index,column="set")
        previous=old.get("profiles",{}).get(key,{})
        origin="previous" if previous.get("origin")=="previous" and previous.get("rows")==clean_rows else "manual"
        photo=photos.get(item.get("photo_id")) if isinstance(item.get("photo_id"),int) else None
        if photo:
            printed_rows=photo.result.get('profiles',{}).get(key,{}).get('rows',[])
            cells_only=lambda rows:[dict(label=r.get('label'),values=r.get('values')) for r in rows]
            if printed_rows and cells_only(printed_rows)==cells_only(clean_rows):origin='photo'
        result["profiles"][key]=dict(rows=clean_rows,status=status,reason=reason,origin=origin,photo_id=photo.id if photo and origin=="photo" else None)
    return result


def gaps(report):
    data=report.data or {};out=[]
    if not data.get("context_confirmed"):out.append(dict(step="identity",context="context_confirmed",label="Zuordnungen und Stammdatenstand bestätigen"))
    for key,label in (("machine_id","Maschine auswählen"),("article_id","Artikel am Werkzeug auswählen"),("material_id","Hauptrohstoff auswählen")):
        if not report.context.get(key):out.append(dict(step="identity",context=key,label=label))
    required={'tool_no','machine_no','article_no','material_no','cycle_target','record_date','operator'}
    if report.context.get('masterbatch_id'):required.update(('batch_no','batch_name','batch_percent'))
    for key,spec in FIELDS.items():
        item=data.get("values",{}).get(key,{})
        if item.get('origin')=='photo' and spec['kind']=='number' and item.get('value') and not safe_scalar(key,item['value']):
            out.append(dict(step=spec['step'],field=key,label='Unsicherer alter Foto-Wert: '+spec['label']))
        if item.get("status") not in ("confirmed","na"):
            out.append(dict(step=spec["step"],field=key,label=spec["label"]))
        if key in required and (item.get("status")!="confirmed" or not item.get("value")):
            if not any(g["label"]==spec["label"] for g in out):out.append(dict(step=spec["step"],field=key,label=spec["label"]+" ist erforderlich"))
    for key,spec in PROFILES.items():
        if data.get("profiles",{}).get(key,{}).get("status") not in ("confirmed","na"):out.append(dict(step=spec["step"],profile=key,label=spec["label"]))
    for key,context_key in (("tool_no","tool_no"),("machine_no","machine_no"),("article_no","article_no"),("material_no","material_no"),("batch_no","batch_no")):
        if report.context.get(context_key) and data.get("values",{}).get(key,{}).get("value")!=report.context[context_key]:
            out.append(dict(step=FIELDS[key]['step'],field=key,label="Nummer widerspricht Zuordnung: "+FIELDS[key]["label"]))
    return out


def snapshot(report, action):
    db.session.flush()
    db.session.add(SetupReportRevision(report_id=report.id,version=report.version,actor_id=current_user.id,
        snapshot=copy.deepcopy(dict(data=report.data,context=report.context,state=report.state,version=report.version))))
    log_change("tool",report.tool_id,"update",{"Einstellbericht":{"old":None,"new":f"Bericht #{report.id} / Stand {report.version}: {action}"}},category="setup_report",entity_name=report.context.get("tool_no"))
