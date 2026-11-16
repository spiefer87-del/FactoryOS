"""Isolated regression: inventory starts recording without any order."""
import copy
import runpy
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from sqlalchemy import event

fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.models import TimeBooking, MachineToolState, MachineControlState, MachineControlCommand
from factoryos.modules.production.services.machine_control_service import snapshot, current_booking
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state
from factoryos.modules.production.services.idle_recording_service import repair_missing_idle
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from factoryos.modules.production.services.booking_service import get_manual_start_data

with app.app_context():
    user=db.session.merge(fixture['user'])
    m=Machine(machine_no='IDLE-NEW',machine_status='aktiv')
    db.session.add(m);db.session.commit()
    args=(m.id,user.id,str(uuid4()),snapshot(m.id)['revision'])
    kw=dict(status='empty',tool_no='',reason='Erstbestand ohne Werkzeug geprüft')
    confirm_tool_state(*args,**kw)
    booking=current_booking(m.id);start=booking.start_time;booking_id=booking.id
    stock=db.session.get(MachineToolState,m.id)
    assert booking.process=='FREI' and booking.order_id is None and start==stock.updated_at
    confirm_tool_state(*args,**kw)
    confirm_tool_state(m.id,user.id,str(uuid4()),snapshot(m.id)['revision'],**kw)
    assert current_booking(m.id).id==booking_id and current_booking(m.id).start_time==start
    lane=next(l for l in get_machine_timeline(now=start+timedelta(seconds=5))['lanes'] if l['machine'].id==m.id)
    assert lane['active_process_label']=='Keine aktive Tätigkeit'
    assert any(i['kind']=='actual' for i in lane['items'])
    assert get_manual_start_data()['active_by_machine'][m.id].process=='FREI'
    # An audit failure must roll the initial interval back with the inventory.
    broken=Machine(machine_no='IDLE-ROLLBACK',machine_status='aktiv');db.session.add(broken);db.session.commit()
    def fail(*args):raise RuntimeError('Synthetic audit failure')
    event.listen(ChangeLog,'before_insert',fail)
    try:
        try:
            confirm_tool_state(broken.id,user.id,str(uuid4()),snapshot(broken.id)['revision'],**kw)
            raise AssertionError('Audit failure not propagated')
        except RuntimeError:db.session.rollback()
    finally:event.remove(ChangeLog,'before_insert',fail)
    assert current_booking(broken.id) is None and db.session.get(MachineToolState,broken.id) is None
    now=datetime.utcnow();past=now-timedelta(hours=2)
    def legacy(name,stamp=past,evidence=True):
        machine=Machine(machine_no=name,machine_status='aktiv');db.session.add(machine);db.session.flush()
        row=MachineToolState(machine_id=machine.id,status='empty',tool_no=None,requires_confirmation=False,updated_by_id=user.id,updated_at=stamp)
        db.session.add(row)
        if evidence:
            db.session.add(MachineControlCommand(command_id=str(uuid4()),machine_id=machine.id,user_id=user.id,source='app',action='confirm_tool',payload_hash='0'*64,
                before_state={'active':[]},after_state={'active':[],'tool_mount':{'status':'empty','tool_no':None,'updated_at':stamp.isoformat()}}))
        db.session.commit();return machine
    old=legacy('IDLE-LEGACY');fallback=legacy('IDLE-NO-EVIDENCE',evidence=False)
    future=legacy('IDLE-FUTURE',now+timedelta(hours=1))
    reserved=legacy('IDLE-RESERVED');db.session.add(MachineControlState(machine_id=reserved.id,version=1,resume_process='RUEST'));db.session.commit()
    intervened=legacy('IDLE-INTERVENED')
    db.session.add(TimeBooking(machine_id=intervened.id,user_id=user.id,process='FREI',type='START',start_time=past+timedelta(minutes=5),end_time=past+timedelta(minutes=10)));db.session.commit()
    receipt=MachineControlCommand.query.filter_by(machine_id=old.id).one();original=copy.deepcopy(receipt.after_state)
    counts=(TimeBooking.query.count(),MachineControlState.query.count(),ChangeLog.query.count())
    preview=repair_missing_idle(check_only=True,now=now)
    assert any(i['machine_id']==old.id for i in preview['created'])
    assert counts==(TimeBooking.query.count(),MachineControlState.query.count(),ChangeLog.query.count())
    result=repair_missing_idle(now=now)
    assert current_booking(old.id).start_time==past
    assert get_manual_start_data()['active_by_machine'][old.id].process=='FREI'
    assert current_booking(fallback.id).start_time==now and current_booking(intervened.id).start_time==now
    assert current_booking(future.id) is None and current_booking(reserved.id) is None
    assert current_booking(m.id).id==booking_id
    assert db.session.get(MachineToolState,old.id).updated_at==past and receipt.after_state==original
    audit=ChangeLog.query.filter_by(category='idle_recording_repair',entity_id=old.id).one()
    assert audit.user_id is None
    count=TimeBooking.query.count();assert not repair_missing_idle(now=now)['created'];assert count==TimeBooking.query.count()
print('PASS: initial idle without order, timeline status, replay/no restart, atomic rollback, dry-run, evidenced backfill, bounded fallback, reservations/future guards, immutable evidence and idempotent repair')
