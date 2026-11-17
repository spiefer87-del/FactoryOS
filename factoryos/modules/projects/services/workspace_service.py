from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo
from flask import abort
from flask_login import current_user
from sqlalchemy import or_
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking
from ..workspace_models import Workspace,Member,WorkTime,WriteLock,Audit

CLOSED=('fertig','finished','closed','gesperrt','locked')
TASK_STATES={'open':'Offen','working':'In Arbeit','waiting':'Wartet auf Ersatzteil','feedback':'Rückmeldung offen','done':'Abgeschlossen'}

def permitted(name):return has_permission(current_user,'projects.'+name)

def mine_clause():
    return or_(Order.project_leader_id==current_user.id,Order.id.in_(db.select(Member.project_id).where(Member.user_id==current_user.id)))

def project(project_id,write=False,manage=False,allow_closed=False):
    item=Order.query.get_or_404(project_id)
    if not item.is_project:abort(404)
    member=item.project_leader_id==current_user.id or db.session.get(Member,(item.id,current_user.id)) is not None
    if not member and not permitted('view_all'):abort(403)
    if write and not member and not permitted('manage'):abort(403)
    if manage and not permitted('manage'):abort(403)
    if write and not allow_closed and item.status in CLOSED:abort(409,'Projekt ist archiviert. Zuerst berechtigt wieder öffnen.')
    return item

def lock():
    if db.session.query(WriteLock).filter_by(id=1).update({WriteLock.revision:WriteLock.revision+1})!=1:abort(503,'Projektmigration zuerst ausführen.')

def version(item,value):
    workspace=db.session.get(Workspace,item.id)
    if not workspace:abort(503,'Projektmigration zuerst ausführen.')
    if str(workspace.version)!=str(value):abort(409,'Projekt wurde inzwischen geändert oder dieses Formular bereits verarbeitet. Bitte neu laden.')
    workspace.version+=1

def audit(item,action,data):db.session.add(Audit(project_id=item.id if item else None,user_id=current_user.id,action=action,data=data))

def required(form,name,maximum=500):
    value=form.get(name,'').strip()
    if not value or len(value)>maximum:raise ValueError(f'{name}: Pflichtfeld, höchstens {maximum} Zeichen.')
    return value

def quantity(value):
    try:result=Decimal(value.replace(',','.'))
    except (InvalidOperation,AttributeError):raise ValueError('Gültige Menge erforderlich.')
    if not result.is_finite() or result<=0 or result>Decimal('999999999') or result.as_tuple().exponent < -3:raise ValueError('Menge muss positiv sein, maximal drei Nachkommastellen.')
    return result

def local_time(value,fold=''):
    try:wall=datetime.fromisoformat(value)
    except (ValueError,TypeError):raise ValueError('Gültiges Datum mit Uhrzeit erforderlich.')
    if wall.tzinfo is not None:raise ValueError('Uhrzeit ohne Zeitzonenangabe eingeben.')
    zone=ZoneInfo('Europe/Berlin');candidates=[]
    for f in (0,1):
        utc=wall.replace(tzinfo=zone,fold=f).astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None)==wall and utc not in [c[1] for c in candidates]:candidates.append((str(f),utc))
    if not candidates:raise ValueError('Diese Uhrzeit existiert wegen der Zeitumstellung nicht.')
    if len(candidates)>1 and fold not in ('0','1'):raise ValueError('Doppelte Uhrzeit: Sommerzeit oder Winterzeit auswählen.')
    return next(utc for f,utc in candidates if len(candidates)==1 or f==fold).replace(tzinfo=None)

def check_interval(user_id,start,end,exclude=None):
    now=datetime.utcnow()
    if start>now or (end and (end<=start or end>now)):raise ValueError('Zeiten müssen in der Vergangenheit liegen; Ende muss nach Start liegen.')
    overlap=WorkTime.query.filter(WorkTime.user_id==user_id,WorkTime.cancelled.is_(False),or_(WorkTime.ended_at.is_(None),WorkTime.ended_at>start))
    if end:overlap=overlap.filter(WorkTime.started_at<end)
    if exclude:overlap=overlap.filter(WorkTime.id!=exclude)
    if overlap.first():raise ValueError('Überschneidung mit einer persönlichen Projektzeit. Zuerst diese Buchung klären.')
    legacy=TimeBooking.query.filter(TimeBooking.user_id==user_id,TimeBooking.process=='PROJEKT',TimeBooking.machine_id.is_(None),or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>start))
    if end:legacy=legacy.filter(TimeBooking.start_time<end)
    if legacy.first():raise ValueError('Überschneidung mit einer bisherigen Projektzeit. Altbuchung zuerst beenden.')

def berlin(value):return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y %H:%M %Z') if value else 'Läuft'
def input_time(value):return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%dT%H:%M:%S') if value else ''
