"""Render supported audit shapes without exposing Python dictionaries or secrets."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from factoryos.extensions import db
from .activity_labels import FIELD_LABELS
from factoryos.modules.sampling.definitions import CHECKS, TEXT_FIELDS, NUMBER_FIELDS, DATE_FIELDS, YES_NO_FIELDS
from factoryos.modules.masterdata.machines.services.machine_excel_schema import KEYS, HEADERS

FIELD_LABELS.update(CHECKS, **TEXT_FIELDS, **DATE_FIELDS, **YES_NO_FIELDS)
FIELD_LABELS.update({key: value[0] for key, value in NUMBER_FIELDS.items()})
FIELD_LABELS.update(dict(zip(KEYS,HEADERS)))
ENTITY_LABELS = {'article':'Artikel','tool':'Werkzeug','machine':'Maschine','material':'Material',
    'order':'Auftrag','sampling':'Musterung','project':'Projekt','customer':'Kunde',
    'user':'Benutzer','role':'Rolle','gauge':'Messmittel','qm_plan':'Prüfplan',
    'inventory':'Lagerjournal','calendar':'Produktionskalender'}
ACTION_LABELS = {'create':'Angelegt','update':'Geändert','delete':'Gelöscht','import':'Importiert',
    'complete':'Abgeschlossen','link_tools':'Werkzeuge zugeordnet','status_update':'Status geändert',
    'tool_status_update':'Werkzeugstatus geändert','password_change':'Passwort geändert',
    'permissions_update':'Berechtigungen geändert','start_review':'Zur Prüfung eingereicht',
    'return_to_draft':'Zur Bearbeitung zurückgegeben','release':'Freigegeben','close':'Geschlossen',
    'auto_close':'Automatisch geschlossen','revision_create':'Neue Revision angelegt',
    'image_add':'Bild hinzugefügt','image_delete':'Bild entfernt','marker_update':'Bildmarkierung geändert',
    'document_add':'Dokumente hinzugefügt','document_delete':'Dokument archiviert',
    'image_primary':'Hauptbild geändert','calibration':'Kalibrierung erfasst'}
ENUMS = {'open':'Offen','offen':'Offen','active':'Aktiv','inactive':'Inaktiv','inspection':'In Prüfung',
    'draft':'Entwurf','review':'In Prüfung','released':'Freigegeben','closed':'Geschlossen',
    'finished':'Abgeschlossen','fertig':'Abgeschlossen','completed':'Erfolgreich abgeschlossen',
    'in_progress':'In Bearbeitung','rework':'Nachbemusterung erforderlich','running':'In Arbeit',
    'locked':'Gesperrt','done':'Erledigt / erfüllt','granted':'Freigabe erteilt',
    'rejected':'Nicht erfüllt / abgelehnt','not_required':'Nicht erforderlich','free':'Verfügbar',
    'blocked':'Gesperrt','reserved':'Reserviert','picked':'Kommissioniert','queued':'Eingeplant',
    'cancel':'Stornieren','edit':'Korrigieren','delete':'Löschen','install':'Einbau','remove':'Ausbau',
    'yes':'Ja','no':'Nein','system_repair':'Systemkorrektur','PROD':'Produktion','MUSTER':'Musterung',
    'RUEST':'Rüsten','FREI':'Frei','PAUSE':'Pause','STOERUNG':'Störung','WARTUNG':'Wartung',
    'SONSTIG':'Sonstiges','PROJEKT':'Projektarbeit','START':'Start','STOP':'Beendet'}
ENUMS.update({'slower':'Langsamer als Sollvergleich','faster':'Schneller als Sollvergleich',
    'overdue':'Soll-Laufzeit überschritten','nominal_reached':'Rechnerisches Sollende erreicht',
    'closure_missing':'Auftragsabschluss fehlt','raw_material':'Rohstoff','masterbatch':'Farbbatch / Masterbatch'})
ENUMS.update({'transition':'Zustandswechsel','inventory':'Bestandsmeldung',
    'setup_wait':'Rüstende mit Wartegrund','wait_reason':'Wartegrund geändert'})
META = {'id','version','command_id','payload_hash','signature','filename','image_path','drawing_path',
        'created_by_id','updated_by_id','reverses_id','recorded_at_utc','is_dirty','bookings','calendar'}
SENSITIVE = {'password','password_hash','old_password','new_password','token','secret','session_secret','csrf_token'}
MISSING = object()

def local_timestamp(value):
    if not value:return 'Zeitpunkt nicht erfasst'
    if isinstance(value,str):value=datetime.fromisoformat(value.replace('Z','+00:00'))
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M %Z')


def hidden_field(field):
    key=str(field).casefold()
    return key in SENSITIVE or (key!='password_changed' and any(word in key for word in ('password','secret','token')))


def empty(value):
    return value is None or value is MISSING or value == ''


def equivalent(old, new):
    if empty(old) and empty(new):
        return True
    # False and zero are meaningful and remain distinguishable from empty values.
    return type(old) is type(new) and old == new


def label(key):
    return FIELD_LABELS.get(key, str(key).replace('_', ' ').strip().capitalize())


def present_change_logs(logs):
    logs = list(logs or [])
    from factoryos.models.user import User
    from factoryos.models.machine import Machine
    from factoryos.modules.orders.models import Order
    from factoryos.modules.masterdata.tools.models import Tool
    from factoryos.modules.masterdata.articles.models import Article
    from factoryos.modules.masterdata.materials.models import Material
    from factoryos.modules.masterdata.customers.models import Customer
    from factoryos.modules.admin.roles.models import Role
    from factoryos.modules.admin.permissions.models import Permission
    from factoryos.modules.admin.permissions.labels import permission_text
    refs = {'tool_id':(Tool,'tool_no'),'tools':(Tool,'tool_no'),'machine_id':(Machine,'machine_no'),
        'order_id':(Order,'order_no'),'article_id':(Article,'article_no'),'material_id':(Material,'material_no'),
        'masterbatch_id':(Material,'material_no'),'customer_id':(Customer,'customer_no'),
        'role_id':(Role,'name'),'user_id':(User,'username'),'released_by_id':(User,'username'),
        'inventory_user_id':(User,'username'),'permission_ids':(Permission,None)}
    ids = {key:set() for key in refs}

    def collect(value, field=''):
        if hidden_field(field) or field in META:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                collect(child, field if key in ('old','new','added','removed') else key)
        elif isinstance(value, (list,tuple)):
            for child in value:collect(child, field)
        elif field in refs and value is not None and not isinstance(value, bool):
            try:ids[field].add(int(value))
            except (TypeError,ValueError):pass

    for log in logs:
        if not getattr(log,'is_project_activity',False):collect(getattr(log,'changes',None))
    resolved = {}
    for field, values in ids.items():
        model, attr = refs[field]
        if values:
            resolved[field] = {row.id:(getattr(row,attr) if attr else permission_text(row)['title'])
                for row in model.query.filter(model.id.in_(values)).all()}

    def format_value(value, field):
        if empty(value):return '—'
        if isinstance(value,bool):return 'Ja' if value else 'Nein'
        if field in refs:
            try:ident=int(value)
            except (TypeError,ValueError):return str(value)
            return str(resolved.get(field,{}).get(ident, f'{label(field)} #{ident}'))
        if isinstance(value,Decimal):return format(value.normalize(),'f').replace('.',',')
        if isinstance(value,float):return format(value,'.15g').replace('.',',')
        raw=str(value)
        if field in ('week_start_day','week_end_day'):
            try:return ('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')[int(value)]
            except (ValueError,IndexError):pass
        if field in ('status','state','workflow_status','action','process','type','source','result','mount_state','setup_state','kind','material_type'):
            return ENUMS.get(raw, raw)
        if field=='machine_type':
            from factoryos.modules.masterdata.shared.constants import MACHINE_TYPES
            return MACHINE_TYPES.get(raw,raw)
        if field == 'category':
            from factoryos.modules.production_deviations.service import REASONS
            return REASONS.get(raw,raw) if isinstance(REASONS,dict) else raw
        if field == 'password_changed':return 'Ja' if value else 'Nein'
        if field=='tool_status':return {'mounted':'Gerüstet','empty':'Abgerüstet','unknown':'Ungeklärt'}.get(raw,raw)
        if field=='reason_code':
            from factoryos.modules.production.services.idle_context_service import WAIT_REASONS
            return WAIT_REASONS.get(raw,raw)
        if field in DATE_FIELDS or field in ('date','last_calibration','next_calibration','calibration_date'):
            try:return datetime.fromisoformat(raw).strftime('%d.%m.%Y')
            except ValueError:pass
        if field.endswith(('_at','_utc','_local')) or field in ('start','end','start_time','end_time'):
            try:
                parsed=datetime.fromisoformat(raw.replace('Z','+00:00'))
                if field.endswith('_local'):return parsed.strftime('%d.%m.%Y %H:%M')
                pattern='%d.%m.%Y %H:%M:%S %Z' if field in ('start_time_utc','end_time_utc') else '%d.%m.%Y %H:%M %Z'
                return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).strftime(pattern)
            except ValueError:pass
        return raw

    result=[]
    for log in logs:
        if getattr(log,'is_project_activity',False):
            result.append(log);continue
        lines=[]

        def add(path, value, old=MISSING, field=''):
            if old is MISSING:
                if not empty(value):lines.append(dict(label=path,value=format_value(value,field),changed=False))
            elif not equivalent(old,value):
                old_text,new_text=format_value(old,field),format_value(value,field)
                if old_text!=new_text:lines.append(dict(label=path,old=old_text,value=new_text,changed=True))

        def walk(field, value, path='', old=MISSING):
            if hidden_field(field) or field in META:return
            name=label(field)
            path=f'{path} · {name}' if path else name
            if field in ('photos','images') and (isinstance(value,(list,tuple)) or isinstance(old,(list,tuple))):
                add(path,len(value) if isinstance(value,(list,tuple)) else MISSING,len(old) if isinstance(old,(list,tuple)) else old,field);return
            if isinstance(value,dict) and ('old' in value or 'new' in value):
                previous=value.get('old',MISSING);current=value.get('new',MISSING)
                # Reasons and other event metadata beside old/new must be retained.
                for key,child in value.items():
                    if key not in ('old','new'):walk(key,child,path)
                if isinstance(current,dict) or isinstance(previous,dict):
                    previous=previous if isinstance(previous,dict) else {}
                    current=current if isinstance(current,dict) else {}
                    for key in dict.fromkeys([*previous,*current]):
                        walk(key,current.get(key,MISSING),path,previous.get(key,MISSING))
                else:walk_value(field,current,path,previous)
            elif isinstance(value,dict) and ('added' in value or 'removed' in value):
                for key,word in (('added','Hinzugefügt'),('removed','Entfernt')):
                    if value.get(key):
                        vals=value[key] if isinstance(value[key],list) else [value[key]]
                        add(path+' · '+word,', '.join(format_value(v,field) for v in vals))
            else:walk_value(field,value,path,old)

        def walk_value(field, value, path, old=MISSING):
            if isinstance(value,dict) or isinstance(old,dict):
                before=old if isinstance(old,dict) else {};after=value if isinstance(value,dict) else {}
                for key in dict.fromkeys([*before,*after]):walk(key,after.get(key,MISSING),path,before.get(key,MISSING))
            elif isinstance(value,(list,tuple)) or isinstance(old,(list,tuple)):
                before=list(old) if isinstance(old,(list,tuple)) else [];after=list(value) if isinstance(value,(list,tuple)) else []
                if all(not isinstance(v,(list,dict,tuple)) for v in before+after):
                    a=', '.join(format_value(v,field) for v in after)
                    b=', '.join(format_value(v,field) for v in before)
                    add(path,a,b if old is not MISSING else MISSING)
                else:
                    for index in range(max(len(before),len(after))):
                        walk_value(field,after[index] if index<len(after) else MISSING,
                            f'{path} · Eintrag {index+1}',before[index] if index<len(before) else MISSING)
            else:add(path,value,old,field)

        changes=getattr(log,'changes',None)
        if isinstance(changes,dict):
            for key,value in changes.items():walk(key,value)
        elif changes is not None:walk('message',changes)
        category=getattr(log,'category',None);action=log.action
        title=ACTION_LABELS.get(action, str(action or 'Aktivität').replace('_',' ').capitalize())
        if category=='article_defect':title={'create':'Fehlereintrag angelegt','update':'Fehlereintrag geändert','delete':'Fehlereintrag gelöscht'}.get(action,'Fehlerkatalog geändert')
        elif category=='article_defect_photo':
            title='Foto aus Fehlerkatalog entfernt'
            data=changes.get('photo',{}) if isinstance(changes,dict) else {}
            snap=data.get('old') or data.get('new') or {}
            lines=[dict(label='Fehlereintrag',value=f"#{snap.get('entry_id','—')}"+(f" · {snap['title']}" if snap.get('title') else ''),changed=False)]
        elif category=='production_deviation':title='Produktionsabweichung bestätigt'
        elif isinstance(changes,dict) and 'booking_end_correction' in changes:title='Produktions-Endzeit korrigiert'
        elif category in ('booking_review','booking_admin_repair'):
            payload=(changes or {}).get('booking_review',(changes or {}).get('admin_repair',{}))
            title={'delete':'Zeitbuchung gelöscht','cancel':'Zeitbuchung storniert','edit':'Zeitbuchung korrigiert'}.get(payload.get('action'),'Zeitbuchung korrigiert')
            original=payload.get('old') or {}
            if original.get('id'):lines.insert(0,dict(label='Zeitbuchung',value=f"#{original['id']}",changed=False))
        elif category=='planning':title='Auftragsplanung geändert'
        elif category=='tool_mount':title='Werkzeugbestand an Maschine geändert'
        elif category=='setup_report':title='Einstellbericht geändert'
        elif category=='order_completion':title='Auftrag abgeschlossen'
        elif category=='qm_plan':title='Prüfplan: '+title
        elif category=='warehouse':title=getattr(log,'action_label',title)
        if not lines:lines=[dict(label='Hinweis',value='Keine weiteren inhaltlichen Änderungen protokolliert.',changed=False)]
        when=format_value(log.created_at.isoformat(),'created_at') if log.created_at else 'Zeitpunkt nicht erfasst'
        result.append(SimpleNamespace(id=log.id,entity_type=log.entity_type,entity_name=log.entity_name or str(log.entity_id),
            entity_id=log.entity_id,entity_label=ENTITY_LABELS.get(log.entity_type,label(log.entity_type)),
            action_label=title,lines=lines,when=when,user=log.user,is_project_activity=False,
            actor_label=getattr(log,'actor_label',None),source=getattr(log,'source','change_log')))
    return result
