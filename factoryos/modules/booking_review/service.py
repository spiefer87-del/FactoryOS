from datetime import datetime
from hashlib import sha256
import json
from sqlalchemy import inspect,select,or_
from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking,QuantityReport,OrderCompletion
from factoryos.modules.production.services.machine_control_service import acquire_control_lock,TERMINAL
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.production.services.booking_time_service import BookingOverlapError

def snapshot(row):
    return {c.name:(getattr(row,c.name).isoformat() if isinstance(getattr(row,c.name),datetime) else getattr(row,c.name)) for c in TimeBooking.__table__.columns}

def related(row):
    conditions=[TimeBooking.machine_id==row.machine_id]
    if row.order_id:conditions.append(TimeBooking.order_id==row.order_id)
    return TimeBooking.query.filter(or_(*conditions)).order_by(TimeBooking.id).all()

def revision(row):return sha256(json.dumps([snapshot(r) for r in related(row)],sort_keys=True).encode()).hexdigest()

def eligible(row):
    if not row.machine_id:raise ValueError('Buchung ohne Maschinenzuordnung bitte zuerst fachlich klären.')
    if not row.end_time:raise ValueError('Laufende Buchung: regulär stoppen oder die bestehende Startzeitkorrektur verwenden. Kein Stornieren im laufenden Betrieb.')
    if row.type=='STORNO':raise ValueError('Diese Buchung wurde bereits storniert und bleibt als Nachweis erhalten.')
    if row.process not in ('PROD','MUSTER','FREI'):raise ValueError('Rüst-, Störungs- und sonstige Zustandsnachweise bitte im jeweiligen Fachablauf klären.')
    if row.order:
        if (row.order.status or '').lower() in TERMINAL or (row.order.sampling and row.order.sampling.state=='completed') or OrderCompletion.query.filter_by(order_id=row.order_id).first():
            raise ValueError('Abgeschlossener/gesperrter Auftrag: keine Änderung seiner historischen Buchungen.')
        if QuantityReport.query.filter_by(order_id=row.order_id).first():raise ValueError('Auftrag besitzt Mengenmeldungen. Buchung erst zusammen mit den bestätigten Produktionsdaten fachlich klären.')
    inspector=inspect(db.engine)
    for table in db.metadata.tables.values():
        for col in table.columns:
            if any(fk.target_fullname=='time_bookings.id' for fk in col.foreign_keys) and inspector.has_table(table.name):
                if db.session.execute(select(col).where(col==row.id).limit(1)).first():
                    raise ValueError('Buchung ist mit einem Fachvorgang verknüpft ('+table.name+'). Diesen zuerst fachlich klären.')

def validate(row,action,start,end,reason):
    eligible(row)
    if not 5<=len(reason.strip())<=1000:raise ValueError('Begründung: bitte 5 bis 1000 Zeichen eingeben.')
    if action=='cancel':return
    if action!='move':raise ValueError('Ungültige Aktion.')
    if not start<end or end>datetime.utcnow():raise ValueError('Zeitbereich: Start muss vor Ende liegen; Ende darf nicht in der Zukunft liegen.')
    if start==row.start_time and end==row.end_time:raise ValueError('Zeitbereich ist unverändert.')
    for other in related(row):
        if other.id!=row.id and (not other.end_time or other.end_time>other.start_time) and other.start_time<end and (other.end_time or datetime.max)>start:
            raise BookingOverlapError(other.id,'Neuer Zeitbereich überschneidet Buchung #'+str(other.id)+'. Keine Änderung gespeichert.')

def apply(row,action,start,end,reason,expected):
    row_id=row.id
    acquire_control_lock();row=db.session.get(TimeBooking,row_id)
    if not row or revision(row)!=expected:raise ValueError('Buchungen wurden inzwischen geändert. Bitte neu laden und erneut prüfen.')
    validate(row,action,start,end,reason)
    old=snapshot(row)
    if action=='cancel':row.end_time=row.start_time;row.type='STORNO'
    else:row.start_time=start;row.end_time=end
    log_change('order' if row.order_id else 'machine',row.order_id or row.machine_id,'update',category='booking_review',entity_name=row.order.order_no if row.order else str(row.machine_id),changes={'booking_review':{'reason':reason.strip(),'action':action,'old':old,'new':snapshot(row)}})
    db.session.commit()
