"""Initial idle intervals from explicit inventory evidence, never production estimates."""
from datetime import datetime
from sqlalchemy import or_
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog
from factoryos.models.user import User
from ..models import TimeBooking,MachineToolState,MachineControlState,MachineControlCommand,SetupOperation


def start_idle_if_unbooked(machine_id,user_id,start_at,*,tool_no=None,note=None):
    """Caller holds acquire_control_lock and owns commit/rollback."""
    from .machine_control_service import ControlConflict
    if TimeBooking.query.filter_by(machine_id=machine_id,end_time=None).first():return None
    overlap=TimeBooking.query.filter(TimeBooking.machine_id==machine_id,
        or_(TimeBooking.start_time>=start_at,TimeBooking.end_time>start_at)).first()
    if overlap:raise ControlConflict('Zeitbuchungen überschneiden den Aufzeichnungsbeginn oder liegen in der Zukunft. Bitte zuerst die Zeitbasis/Buchungen prüfen.')
    booking=TimeBooking(machine_id=machine_id,user_id=user_id,order_id=None,process='FREI',type='START',
        start_time=start_at,tool_no=tool_no,comment=note or 'Erstaufzeichnung: keine aktive Tätigkeit ab bestätigtem Werkzeugbestand')
    db.session.add(booking)
    return booking


def repair_missing_idle(*,check_only=False,now=None):
    """For previously confirmed machines only; no reads/GETs create bookings.

    Earliest safe start is the evidenced latest inventory confirmation. If an
    actual activity intervened or evidence is incomplete, begin at repair time.
    """
    from .machine_control_service import acquire_control_lock
    if not check_only:acquire_control_lock()
    now=now or datetime.utcnow()
    result=dict(created=[],skipped=[])
    for stock in MachineToolState.query.filter(MachineToolState.status.in_(('empty','mounted'))).order_by(MachineToolState.machine_id):
        machine_id=stock.machine_id
        def skip(reason):result['skipped'].append(dict(machine_id=machine_id,reason=reason))
        if stock.requires_confirmation:skip('Bestand muss erneut geprüft werden');continue
        if TimeBooking.query.filter_by(machine_id=machine_id,end_time=None).first():skip('Zeitaufzeichnung läuft bereits');continue
        control=db.session.get(MachineControlState,machine_id)
        if (control and (control.resume_process or control.resume_order_id or control.resume_tool_no)) or SetupOperation.query.filter_by(machine_id=machine_id,outcome='active').first():
            skip('Offener Vorgang oder Reservierung muss zuerst geklärt werden');continue
        if not stock.machine or not db.session.get(User,stock.updated_by_id):skip('Ursprungszuordnung fehlt');continue
        if not stock.updated_at or stock.updated_at>now:skip('Bestandsmeldung liegt in der Zukunft oder hat keinen Zeitstempel');continue
        receipt=MachineControlCommand.query.filter_by(machine_id=machine_id,action='confirm_tool').order_by(MachineControlCommand.id.desc()).first()
        evidence=(receipt.after_state or {}).get('tool_mount',{}) if receipt else {}
        proven=bool(receipt and receipt.user_id==stock.updated_by_id and (receipt.before_state or {}).get('active')==[]
            and (receipt.after_state or {}).get('active')==[] and evidence.get('updated_at')==stock.updated_at.isoformat()
            and evidence.get('status')==stock.status and evidence.get('tool_no')==stock.tool_no)
        intervening=TimeBooking.query.filter(TimeBooking.machine_id==machine_id,
            or_(TimeBooking.start_time>=stock.updated_at,TimeBooking.end_time>stock.updated_at)).first()
        start=stock.updated_at if proven and not intervening else now
        overlapping=TimeBooking.query.filter(TimeBooking.machine_id==machine_id,
            or_(TimeBooking.start_time>=start,TimeBooking.end_time>start)).first()
        if overlapping:skip('Spätere/Zukunftsbuchung verhindert einen widerspruchsfreien Beginn');continue
        item=dict(machine_id=machine_id,machine_no=stock.machine.machine_no,start_at=start.isoformat(),
            basis='Bestätigte Bestandsmeldung ohne aktive Buchung' if start==stock.updated_at and proven else 'Beginn zum Reparaturzeitpunkt',
            source_command_id=receipt.command_id if proven else None)
        if not check_only:
            booking=start_idle_if_unbooked(machine_id,stock.updated_by_id,start,
                tool_no=stock.tool_no if stock.status=='mounted' else None,
                note='Systemnachtrag: keine aktive Tätigkeit; Bezug auf die protokollierte Bestandsmeldung, kein neuer Produktions-/Rüststart')
            if not booking:skip('Zeitaufzeichnung wurde inzwischen begonnen');continue
            if not control:control=MachineControlState(machine_id=machine_id,version=0);db.session.add(control)
            control.version+=1;db.session.flush();item['booking_id']=booking.id
            db.session.add(ChangeLog(entity_type='machine',entity_id=machine_id,entity_name=stock.machine.machine_no,
                action='update',category='idle_recording_repair',user_id=None,
                changes={'initial_idle_recording':{'old':None,'new':{**item,'source':'system_repair',
                    'inventory_user_id':stock.updated_by_id,'recorded_at_utc':now.isoformat()}}}))
        result['created'].append(item)
    if not check_only:db.session.commit()
    return result
