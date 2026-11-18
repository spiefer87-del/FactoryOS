"""Explicit system-admin repair; original facts are always retained in the audit log."""
from datetime import datetime
from hashlib import sha256
import json
from sqlalchemy import inspect,text,or_
from flask_login import current_user
from factoryos.core.auth import is_system_admin
from factoryos.extensions import db
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.production.models import TimeBooking,SetupOperation,ProductionPlanEntry,MachineControlState,MachineToolState,QuantityReport,OrderCompletion
from factoryos.modules.production.services.machine_control_service import acquire_control_lock
from .service import snapshot,operation_snapshot,assert_no_references

def operations(row):
    query=SetupOperation.query.filter_by(machine_id=row.machine_id)
    return query.filter(or_(SetupOperation.start_booking_id==row.id,
        (SetupOperation.kind==row.process)&(SetupOperation.started_at< (row.end_time or datetime.max))&or_(SetupOperation.ended_at.is_(None),SetupOperation.ended_at>row.start_time))).order_by(SetupOperation.id).all() if row.process in ('RUEST','ABRUEST') else query.filter_by(start_booking_id=row.id).all()

def revision(row):
    # Include dependent records, without loading unrelated factory history.
    clauses={'time_bookings':'machine_id=:machine OR order_id=:order','setup_operations':'machine_id=:machine','production_plan_entries':'machine_id=:machine OR order_id=:order','machine_control_states':'machine_id=:machine','machine_tool_states':'machine_id=:machine','quantity_reports':'order_id=:order','order_completions':'order_id=:order','orders':'id=:order'}
    def rows(table,clause):return [list(r) for r in db.session.execute(text('SELECT * FROM '+db.engine.dialect.identifier_preparer.quote(table)+' WHERE '+clause+' ORDER BY 1'),{'machine':row.machine_id,'order':row.order_id})]
    clauses['booking_idle_contexts']='booking_id IN (SELECT id FROM time_bookings WHERE machine_id=:machine OR order_id=:order)'
    payload={t:rows(t,clause) for t,clause in clauses.items() if inspect(db.engine).has_table(t)}
    return sha256(json.dumps(payload,default=str,sort_keys=True).encode()).hexdigest()

def plan(row,action,start,end,reason):
    if action not in ('move','delete'):raise ValueError('Ungültige Reparaturaktion.')
    if not 10<=len(reason.strip())<=1000:raise ValueError('Bitte eine nachvollziehbare Begründung mit 10 bis 1000 Zeichen eingeben.')
    if not row.machine_id:raise ValueError('Maschinenzuordnung fehlt. Diese muss vor der Reparatur geklärt werden.')
    if action=='move':
        if start>datetime.utcnow() or (end and end>datetime.utcnow()):raise ValueError('Tatsächliche Zeiten dürfen nicht in der Zukunft liegen.')
        if end and end<start:raise ValueError('Ende darf nicht vor Start liegen.')
    warnings=[]
    if action=='move' and end==start:warnings.append('Nullzeit: Die Buchung wird als STORNO aus der Zeitwertung genommen.')
    elif action=='move' and row.type=='STORNO':warnings.append('Diese STORNO-Buchung wird ausdrücklich als START reaktiviert und zählt wieder zur Zeitwertung.')
    if row.order_id:
        if QuantityReport.query.filter_by(order_id=row.order_id).first() or OrderCompletion.query.filter_by(order_id=row.order_id).first():warnings.append('Bestätigte Mengen/Abschluss vorhanden. Mengen und Lager bleiben unverändert; Zeitkennzahlen ändern sich.')
        if row.order and (row.order.status in ('fertig','finished','locked','gesperrt') or (row.order.sampling and row.order.sampling.state=='completed')):warnings.append('Historischer/abgeschlossener Auftrag. Seine Freigabe wird durch die Zeitreparatur nicht geändert.')
    if row.end_time is None:warnings.append('Laufende Buchung wird repariert. Dies ist kein elektrischer Maschinenstopp. Bedienzustand anschließend kontrollieren.')
    if action=='move':
        conflicts=TimeBooking.query.filter(TimeBooking.id!=row.id,TimeBooking.machine_id==row.machine_id,TimeBooking.start_time<(end or datetime.max),or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>start)).filter(or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>TimeBooking.start_time)).all()
        if conflicts:warnings.append('Überschneidung bleibt mit Buchung(en) '+', '.join('#'+str(r.id) for r in conflicts)+'. Diese müssen anschließend separat bereinigt werden.')
        if end is None and TimeBooking.query.filter(TimeBooking.id!=row.id,TimeBooking.machine_id==row.machine_id,TimeBooking.end_time.is_(None)).first():raise ValueError('Eine weitere laufende Buchung darf nicht entstehen. Zuerst andere laufende Buchungen beenden oder reparieren.')
    ops=[]
    for op in operations(row):
        if op.kind!=row.process or op.machine_id!=row.machine_id or op.tool_no!=row.tool_no or op.order_id!=row.order_id:raise ValueError('Widersprüchliche Werkzeug-/Auftragszuordnung im Rüstnachweis #'+str(op.id)+'. Keine automatische Umzuordnung möglich.')
        segments=TimeBooking.query.filter(TimeBooking.machine_id==row.machine_id,TimeBooking.process==op.kind,TimeBooking.order_id==op.order_id,TimeBooking.tool_no==op.tool_no,TimeBooking.id>=op.start_booking_id,TimeBooking.start_time<(op.ended_at or datetime.max),or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>op.started_at)).filter(or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>TimeBooking.start_time)).order_by(TimeBooking.start_time,TimeBooking.id).all()
        segments=[s for s in segments if s.id!=row.id]
        times=[dict(id=s.id,start=s.start_time,end=s.end_time) for s in segments]
        if action=='move':times.append(dict(id=row.id,start=start,end=end))
        if not times:
            assert_no_references('setup_operations',op.id)
            ops.append(dict(id=op.id,action='delete',old=operation_snapshot(op)))
        else:
            times.sort(key=lambda s:(s['start'],s['id']))
            if any(s['end'] is None for s in times) and op.outcome!='active':raise ValueError('Abgeschlossener Rüstnachweis darf keine laufende Teilbuchung bekommen. Bitte Endzeit angeben.')
            new_start=min(s['start'] for s in times)
            still_active=any(s['end'] is None for s in times)
            new_outcome=op.outcome if still_active or op.outcome!='active' else 'aborted'
            new_end=None if still_active else max(s['end'] for s in times)
            # Repair stale closed boundaries from the actual retained work segments.
            ops.append(dict(id=op.id,action='update',start=new_start,end=new_end,first=times[0]['id'],outcome=new_outcome,old=operation_snapshot(op)))
        warnings.append('Rüstnachweis #'+str(op.id)+' wird aus den verbleibenden Rüst-Teilbuchungen gemeinsam korrigiert oder entfernt; ursprüngliche Grenzen bleiben im Protokoll.')
    if action=='delete':
        for entry in ProductionPlanEntry.query.filter_by(started_booking_id=row.id):warnings.append('Planreferenz #'+str(entry.id)+' wird von der gelöschten Buchung gelöst; Planstatus bleibt unverändert.')
        # Only explicitly understood references may be detached; unknown extensions fail closed.
        inspector=inspect(db.engine);quote=db.engine.dialect.identifier_preparer.quote
        for table in inspector.get_table_names():
            for fk in inspector.get_foreign_keys(table):
                if fk.get('referred_table')!='time_bookings':continue
                for col,remote in zip(fk['constrained_columns'],fk['referred_columns']):
                    if remote!='id' or (table,col) in (('setup_operations','start_booking_id'),('production_plan_entries','started_booking_id'),('booking_idle_contexts','booking_id')):continue
                    if db.session.execute(text('SELECT 1 FROM '+quote(table)+' WHERE '+quote(col)+'=:id LIMIT 1'),{'id':row.id}).first():raise ValueError('Unbekannter abhängiger Fachvorgang '+table+'. Keine Löschung; diese Verknüpfung muss fachlich geklärt werden.')
        warnings.append('Vollständiges Löschen ohne Papierkorb. Originaldaten bleiben im Änderungsprotokoll und in vorherigen Sicherungen.')
    return dict(operations=ops,warnings=warnings)

def apply(row,action,start,end,reason,expected):
    if not is_system_admin(current_user):raise PermissionError('Nur Systemadministratoren.')
    row_id=row.id;machine_id=row.machine_id
    acquire_control_lock();row=db.session.get(TimeBooking,row_id)
    if not is_system_admin(current_user):raise PermissionError('Administrationsberechtigung wurde geändert.')
    if not row or revision(row)!=expected:raise ValueError('Daten seit der Vorschau geändert. Bitte erneut prüfen.')
    repair=plan(row,action,start,end,reason)
    old=snapshot(row);was_active=row.end_time is None
    plans=[]
    if action=='delete':
        for entry in ProductionPlanEntry.query.filter_by(started_booking_id=row.id):
            plans.append(dict(id=entry.id,old_booking_id=entry.started_booking_id));entry.started_booking_id=None
    for item in repair['operations']:
        op=db.session.get(SetupOperation,item['id'])
        if item['action']=='delete':db.session.delete(op)
        else:
            op.started_at=item['start'];op.ended_at=item['end'];op.start_booking_id=item['first'];op.outcome=item['outcome']
            if item['old']['outcome']=='active' and item['outcome']=='aborted':op.ended_by_id=current_user.id;op.note=('Admin-Reparatur: '+reason.strip())[:255]
    db.session.flush()
    if action=='delete':db.session.delete(row)
    else:
        row.start_time=start;row.end_time=end
        if end==start:row.type='STORNO'
        elif row.type=='STORNO':row.type='START'
    control=db.session.get(MachineControlState,machine_id)
    old_control=None
    if control:
        old_control=dict(version=control.version,resume_process=control.resume_process,resume_order_id=control.resume_order_id,resume_tool_no=control.resume_tool_no)
        control.version+=1
        if was_active and (action=='delete' or end is not None):control.resume_process=None;control.resume_order_id=None;control.resume_tool_no=None
    stock=db.session.get(MachineToolState,machine_id);stock_note=None
    repaired_open_op=any(item['old']['outcome']=='active' and (item['action']=='delete' or item.get('outcome')=='aborted') for item in repair['operations'])
    if stock and (repaired_open_op or (was_active and row.process in ('RUEST','ABRUEST') and (action=='delete' or end is not None))):
        stock_note=dict(previous_status=stock.status,previous_requires_confirmation=stock.requires_confirmation)
        stock.requires_confirmation=True  # Never infer mounted/empty from a time repair.
    data={'action':action,'reason':reason.strip(),'old':old,'new':None if action=='delete' else snapshot(row),'setup_changes':repair['operations'],'plan_references':plans,'control_before':old_control,'tool_confirmation':stock_note,'warnings':repair['warnings']}
    # Datetimes in the repair plan are converted for JSON audit storage.
    data=json.loads(json.dumps(data,default=lambda value:value.isoformat() if isinstance(value,datetime) else str(value)))
    log_change('order' if old['order_id'] else 'machine',old['order_id'] or machine_id,'delete' if action=='delete' else 'update',category='booking_admin_repair',entity_name=row.order.order_no if row.order else str(machine_id),changes={'admin_repair':data})
    db.session.commit()
