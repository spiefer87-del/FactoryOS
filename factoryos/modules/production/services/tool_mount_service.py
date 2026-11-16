"""Verified physical tooling is independent of the current time-booking process."""
from datetime import datetime
import hashlib
import json
from uuid import UUID
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.models.change_log import ChangeLog
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.masterdata.tools.models import Tool
from ..models import MachineToolState,SetupOperation,TimeBooking,MachineControlState,MachineControlCommand


def tool_snapshot(machine_id):
    state=db.session.get(MachineToolState,machine_id)
    operation=SetupOperation.query.filter_by(machine_id=machine_id,outcome='active').first()
    return dict(status=state.status if state else 'unknown',tool_no=state.tool_no if state else None,
        requires_confirmation=state.requires_confirmation if state else False,
        updated_at=state.updated_at.isoformat() if state else None,
        operation=dict(id=operation.id,kind=operation.kind,tool_no=operation.tool_no,started_at=operation.started_at.isoformat()) if operation else None)


def tool_label(value):
    if value['operation']:return ('Abrüstvorgang offen: ' if value['operation']['kind']=='ABRUEST' else 'Rüstvorgang offen: ')+value['operation']['tool_no']
    if value['status']=='mounted':return 'Gerüstet · Werkzeug '+str(value['tool_no'])+' montiert'
    if value['status']=='empty':return 'Abgerüstet · ohne Werkzeug bestätigt'
    return 'Werkzeugbestand ungeklärt'+(' · zuletzt '+str(value['tool_no']) if value['tool_no'] else '')


def assert_tool_available(tool_no,machine_id):
    from .machine_control_service import ControlConflict
    mounted=MachineToolState.query.filter(MachineToolState.machine_id!=machine_id,
        MachineToolState.tool_no==tool_no,MachineToolState.status=='mounted').first()
    pending=SetupOperation.query.filter(SetupOperation.machine_id!=machine_id,
        SetupOperation.tool_no==tool_no,SetupOperation.outcome=='active').first()
    if mounted or pending:
        other=mounted.machine if mounted else pending.machine
        raise ControlConflict('Werkzeug '+tool_no+' ist auf '+other.machine_no+' montiert oder im Rüstvorgang gebunden. Dort erst regulär abrüsten bzw. Bestand klären.')


def apply_transition(machine_id,user_id,action,active,next_process,next_tool,next_order,booking,command_id,comment,now):
    """Inside the authoritative machine lock/transaction; never commits here."""
    from .machine_control_service import ControlConflict
    state=db.session.get(MachineToolState,machine_id)
    op=SetupOperation.query.filter_by(machine_id=machine_id,outcome='active').first()
    if action in ('start','resume') and next_process in ('PROD','MUSTER'):
        if op:raise ControlConflict('Rüstvorgang zuerst ausdrücklich abschließen oder abbrechen.')
        if state and state.requires_confirmation:raise ControlConflict('Werkzeugbestand nach abgebrochenem/ungeklärtem Rüsten zuerst prüfen und bestätigen.')
        if state and state.status=='empty':raise ControlConflict('Maschine ist als abgerüstet bestätigt. Werkzeug zuerst aufrüsten und Rüstende bestätigen.')
        if state and state.status=='mounted' and state.tool_no!=next_tool:raise ControlConflict('Montiertes Werkzeug '+state.tool_no+' passt nicht zum Auftrag. Erst abrüsten und passendes Werkzeug aufrüsten.')
        if next_tool:assert_tool_available(next_tool,machine_id)
        # Legacy starts remain possible, but an unverified reference NEVER becomes
        # a confirmed mount merely because production was booked.
        if not state:
            state=MachineToolState(machine_id=machine_id,status='unknown',tool_no=next_tool,
                updated_by_id=user_id,updated_at=now,requires_confirmation=False);db.session.add(state)
    if action in ('setup','unsetup'):
        if op:raise ControlConflict('Ein Rüstvorgang ist bereits offen.')
        if state and state.requires_confirmation:raise ControlConflict('Vor einem neuen Rüstvorgang zuerst den tatsächlichen Werkzeugbestand klären.')
        if state and state.status=='mounted' and state.tool_no!=next_tool:raise ControlConflict('Anderes Werkzeug ist noch montiert. Zuerst das montierte Werkzeug abrüsten.')
        if action=='unsetup' and state and state.status=='empty':raise ControlConflict('Maschine ist bereits ohne Werkzeug bestätigt.')
        assert_tool_available(next_tool,machine_id)
        if not state:
            state=MachineToolState(machine_id=machine_id,updated_by_id=user_id);db.session.add(state)
        state.status='unknown';state.tool_no=next_tool;state.requires_confirmation=True
        state.updated_at=now;state.updated_by_id=user_id
        db.session.add(SetupOperation(machine_id=machine_id,order_id=next_order,tool_no=next_tool,
            kind=next_process,outcome='active',started_at=now,started_by_id=user_id,start_booking_id=booking.id))
    elif action=='finish_setup':
        # Old active setups have no new operation record. Their end still requires
        # explicit operator action and confirms only the tool in that booking.
        kind=op.kind if op else active.process
        tool=op.tool_no if op else active.tool_no
        if not tool:raise ControlConflict('Werkzeugbezug fehlt. Vorgang abbrechen und Bestand prüfen.')
        if kind=='RUEST':assert_tool_available(tool,machine_id)
        if not state:state=MachineToolState(machine_id=machine_id,updated_by_id=user_id);db.session.add(state)
        state.status='mounted' if kind=='RUEST' else 'empty';state.tool_no=tool if kind=='RUEST' else None
        state.requires_confirmation=False;state.updated_at=now;state.updated_by_id=user_id
        if op:
            op.outcome='completed';op.ended_at=now;op.ended_by_id=user_id;op.end_command_id=command_id;op.note=comment or None
    elif action=='stop' and (op or (active and active.process in ('RUEST','ABRUEST'))):
        if op:
            op.outcome='aborted';op.ended_at=now;op.ended_by_id=user_id;op.end_command_id=command_id;op.note=comment
        if not state:
            state=MachineToolState(machine_id=machine_id,updated_by_id=user_id,tool_no=active.tool_no);db.session.add(state)
        state.status='unknown';state.requires_confirmation=True;state.updated_at=now;state.updated_by_id=user_id
    # Pauses, faults, maintenance, stops and order completion never remove tooling.
    if next_process=='FREI' and state:
        booking.tool_no=state.tool_no


def operation_times(operation,now=None):
    end=operation.ended_at or now or datetime.utcnow()
    segments=TimeBooking.query.filter(TimeBooking.machine_id==operation.machine_id,
        TimeBooking.start_time>=operation.started_at,TimeBooking.start_time<end,
        TimeBooking.id>=operation.start_booking_id).all()
    work=sum(max(0,(min(b.end_time or end,end)-b.start_time).total_seconds())
        for b in segments if b.process==operation.kind)
    total=max(0,(end-operation.started_at).total_seconds())
    return dict(work=work,interruptions=max(0,total-work),total=total)


def confirm_tool_state(machine_id,user_id,command_id,revision,*,status,tool_no='',reason=''):
    from .machine_control_service import acquire_control_lock,snapshot,current_booking,ControlConflict,ControlDenied
    user=db.session.get(User,user_id)
    if not has_permission(user,'production.setup'):raise ControlDenied('Keine Berechtigung zur Werkzeugbestätigung.')
    try:
        if str(UUID(command_id))!=command_id:raise ValueError()
    except (TypeError,ValueError,AttributeError):raise ValueError('Ungültige Bestätigungskennung. Bitte neu laden.')
    tool_no=(tool_no or '').strip();reason=(reason or '').strip()
    if status not in ('mounted','empty'):raise ValueError('Bitte montiertes Werkzeug oder ohne Werkzeug auswählen.')
    if len(reason)<5 or len(reason)>255:raise ValueError('Bestandsprüfung bitte mit 5 bis 255 Zeichen begründen.')
    if status=='empty':tool_no=None
    digest=hashlib.sha256(json.dumps(dict(revision=revision,status=status,tool_no=tool_no,reason=reason),sort_keys=True).encode()).hexdigest()
    acquire_control_lock();user=db.session.get(User,user_id)
    if not has_permission(user,'production.setup'):raise ControlDenied('Berechtigung wurde geändert.')
    machine=db.session.get(Machine,machine_id)
    if not machine:raise ValueError('Maschine fehlt.')
    receipt=MachineControlCommand.query.filter_by(command_id=command_id).first()
    if receipt:
        if receipt.user_id!=user_id or receipt.machine_id!=machine_id or receipt.action!='confirm_tool' or receipt.payload_hash!=digest:raise ControlConflict('Befehlskennung bereits anders verwendet.')
        db.session.commit();return receipt,True
    before=snapshot(machine_id)
    if before['revision']!=revision:raise ControlConflict('Maschinenstand geändert. Bitte neu laden und Bestand erneut prüfen.')
    if len(before['active'])>1 or SetupOperation.query.filter_by(machine_id=machine_id,outcome='active').first():raise ControlConflict('Laufenden Rüstvorgang oder mehrdeutige Buchungen zuerst klären.')
    active=current_booking(machine_id)
    if active and active.process!='FREI':
        expected_tool=active.tool_no or (active.order.tool_no if active.order else None)
        if active.process not in ('PROD','MUSTER') or status!='mounted' or tool_no!=expected_tool:
            raise ControlConflict('Während eines laufenden Vorgangs darf nur das zugehörige montierte Werkzeug bestätigt werden. Sonst zuerst regulär stoppen.')
    if status=='mounted':
        if not tool_no or not Tool.query.filter_by(tool_no=tool_no).first():raise ValueError('Vorhandenes Werkzeug aus den Stammdaten auswählen.')
        assert_tool_available(tool_no,machine_id)
    state=db.session.get(MachineToolState,machine_id)
    if not state:state=MachineToolState(machine_id=machine_id,updated_by_id=user_id);db.session.add(state)
    state.status=status;state.tool_no=tool_no;state.requires_confirmation=False;state.updated_by_id=user_id;state.updated_at=datetime.utcnow()
    control=db.session.get(MachineControlState,machine_id)
    if not control:control=MachineControlState(machine_id=machine_id,version=0);db.session.add(control)
    control.version+=1;db.session.flush()
    after=snapshot(machine_id)
    receipt=MachineControlCommand(command_id=command_id,machine_id=machine_id,user_id=user_id,source='app',action='confirm_tool',
        payload_hash=digest,comment=reason,before_state=before,after_state=after);db.session.add(receipt)
    db.session.add(ChangeLog(entity_type='machine',entity_id=machine_id,entity_name=machine.machine_no,action='update',
        category='tool_mount',user_id=user_id,changes={'tool_mount':{'old':before['tool_mount'],'new':after['tool_mount']},'reason':{'old':None,'new':reason}}))
    db.session.commit();return receipt,False
