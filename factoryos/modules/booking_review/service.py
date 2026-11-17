from datetime import datetime
from hashlib import sha256
import json
from sqlalchemy import inspect,text,or_
from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking,QuantityReport,OrderCompletion,SetupOperation
from factoryos.modules.production.services.machine_control_service import acquire_control_lock,TERMINAL
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.production.services.booking_time_service import BookingOverlapError

def snapshot(row):
    return {c.name:(getattr(row,c.name).isoformat() if isinstance(getattr(row,c.name),datetime) else getattr(row,c.name)) for c in TimeBooking.__table__.columns}

def related(row):
    conditions=[TimeBooking.machine_id==row.machine_id]
    if row.order_id:conditions.append(TimeBooking.order_id==row.order_id)
    return TimeBooking.query.filter(or_(*conditions)).order_by(TimeBooking.id).all()

def operation_snapshot(op):
    return {c.name:(getattr(op,c.name).isoformat() if isinstance(getattr(op,c.name),datetime) else getattr(op,c.name)) for c in SetupOperation.__table__.columns}

def revision(row):
    operations=SetupOperation.query.filter_by(machine_id=row.machine_id).order_by(SetupOperation.id).all()
    return sha256(json.dumps({'bookings':[snapshot(r) for r in related(row)],'operations':[operation_snapshot(op) for op in operations]},sort_keys=True).encode()).hexdigest()

def setup_operation(row):
    operations=SetupOperation.query.filter_by(start_booking_id=row.id).all()
    if len(operations)>1:raise ValueError('Mehrere Rüstnachweise verweisen auf diese Buchung. Bitte gemeinsam fachlich klären.')
    if not operations:
        if row.process in ('RUEST','ABRUEST'):
            overlap=SetupOperation.query.filter(SetupOperation.machine_id==row.machine_id,SetupOperation.started_at<row.end_time,or_(SetupOperation.ended_at.is_(None),SetupOperation.ended_at>row.start_time)).first()
            if overlap:raise ValueError('Teilbuchung eines mehrteiligen Rüstvorgangs: nicht einzeln verändern. Den gesamten Rüstvorgang zuerst fachlich klären.')
        return None
    op=operations[0]
    if row.process not in ('RUEST','ABRUEST') or op.kind!=row.process or op.machine_id!=row.machine_id or op.order_id!=row.order_id or op.tool_no!=row.tool_no:
        raise ValueError('Rüstnachweis und Buchung sind nicht konsistent zugeordnet. Bitte zuerst fachlich klären.')
    if op.outcome not in ('completed','aborted') or op.started_at!=row.start_time or op.ended_at!=row.end_time:
        raise ValueError('Offener oder mehrteiliger Rüstvorgang: dieser kann hier nicht einzeln verändert werden.')
    if TimeBooking.query.filter(TimeBooking.machine_id==row.machine_id,TimeBooking.id!=row.id,TimeBooking.start_time<row.end_time,or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>row.start_time)).filter(or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>TimeBooking.start_time)).first():
        raise ValueError('Rüstzeit enthält weitere Buchungen. Diese müssen gemeinsam fachlich geklärt werden.')
    return op

def assert_no_references(target,record_id,allowed=None):
    inspector=inspect(db.engine)
    quote=db.engine.dialect.identifier_preparer.quote
    for table in inspector.get_table_names():
        for foreign in inspector.get_foreign_keys(table):
            if foreign.get('referred_table')!=target:continue
            for col,remote in zip(foreign['constrained_columns'],foreign['referred_columns']):
                if remote!='id' or (table,col)==allowed:continue
                query=text('SELECT 1 FROM '+quote(table)+' WHERE '+quote(col)+'=:record_id LIMIT 1')
                if db.session.execute(query,{'record_id':record_id}).first():
                    raise ValueError('Verknüpfter Fachvorgang ('+table+'): zuerst gemeinsam fachlich klären.')

def eligible(row,action='move'):
    if not row.machine_id:raise ValueError('Buchung ohne Maschinenzuordnung bitte zuerst fachlich klären.')
    if not row.end_time:raise ValueError('Laufende Buchung: regulär stoppen oder die bestehende Startzeitkorrektur verwenden. Kein Stornieren im laufenden Betrieb.')
    if row.type=='STORNO' and action!='delete':raise ValueError('Diese Buchung wurde bereits storniert. Nur vollständiges Löschen mit entsprechendem Recht ist noch möglich.')
    if row.process not in ('PROD','MUSTER','FREI','RUEST','ABRUEST'):raise ValueError('Störungs- und sonstige Zustandsnachweise bitte im jeweiligen Fachablauf klären.')
    if row.order:
        if (row.order.status or '').lower() in TERMINAL or (row.order.sampling and row.order.sampling.state=='completed') or OrderCompletion.query.filter_by(order_id=row.order_id).first():
            raise ValueError('Abgeschlossener/gesperrter Auftrag: keine Änderung seiner historischen Buchungen.')
        if QuantityReport.query.filter_by(order_id=row.order_id).first():raise ValueError('Auftrag besitzt Mengenmeldungen. Buchung erst zusammen mit den bestätigten Produktionsdaten fachlich klären.')
    op=setup_operation(row)
    assert_no_references('time_bookings',row.id,('setup_operations','start_booking_id') if op else None)
    if op:
        if action=='cancel':raise ValueError('Verknüpfter Rüstnachweis: bitte Zeitbereich korrigieren oder Buchung und Nachweis gemeinsam vollständig löschen.')
        if action=='delete':assert_no_references('setup_operations',op.id)

def validate(row,action,start,end,reason):
    eligible(row,action)
    if not 5<=len(reason.strip())<=1000:raise ValueError('Begründung: bitte 5 bis 1000 Zeichen eingeben.')
    if action in ('cancel','delete'):return
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
    op=setup_operation(row)
    old_op=operation_snapshot(op) if op else None
    entity_type='order' if row.order_id else 'machine';entity_id=row.order_id or row.machine_id
    entity_name=row.order.order_no if row.order else str(row.machine_id)
    if action=='delete':
        if op:db.session.delete(op);db.session.flush()
        db.session.delete(row)
    elif action=='cancel':row.end_time=row.start_time;row.type='STORNO'
    else:row.start_time=start;row.end_time=end
    if op and action=='move':op.started_at=start;op.ended_at=end
    log_change(entity_type,entity_id,'delete' if action=='delete' else 'update',category='booking_review',entity_name=entity_name,changes={'booking_review':{'reason':reason.strip(),'action':action,'old':old,'new':None if action=='delete' else snapshot(row),'setup_old':old_op,'setup_new':operation_snapshot(op) if op and action!='delete' else None}})
    db.session.commit()
