"""Isolated tool inventory and setup lifecycle. Never production data/hardware."""
import copy
import re
import runpy
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import MachineToolState,SetupOperation,TimeBooking,ProductionPlanEntry
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking,ControlConflict
from factoryos.modules.production.services.tool_mount_service import tool_snapshot,confirm_tool_state,operation_times
from factoryos.modules.production.services.order_completion_service import complete_order,completion_context
from factoryos.modules.production.services.planning_service import build_schedule
from factoryos.modules.masterdata.tools.services.tool_service import delete_tool,update_tool
from scripts.upgrade_tool_mount import run_upgrade

with app.app_context():
    user=db.session.merge(fixture['user'])
    old=[(b.id,b.start_time,b.end_time,b.tool_no) for b in TimeBooking.query.all()]
    run_upgrade(True);run_upgrade();run_upgrade()
    assert old==[(b.id,b.start_time,b.end_time,b.tool_no) for b in TimeBooking.query.all()]
    m=Machine(machine_no='MOUNT-1',machine_status='aktiv');other=Machine(machine_no='MOUNT-2',machine_status='aktiv')
    ta=Tool(tool_no='MOUNT-A',name='Tool A');tb=Tool(tool_no='MOUNT-B',name='Tool B')
    oa=Order(order_no='MOUNT-A',article='A001',tool_no=ta.tool_no,target_qty=100,cycle_time_s=30)
    ob=Order(order_no='MOUNT-B',article='A001',tool_no=tb.tool_no,target_qty=100,cycle_time_s=30)
    db.session.add_all([m,other,ta,tb,oa,ob]);db.session.commit()
    def run(action,machine=m,stamp=None,**kwargs):
        args=(machine.id,user.id,action,str(uuid4()),snapshot(machine.id)['revision'])
        if stamp:
            with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
                clock.utcnow.return_value=stamp;return execute(*args,**kwargs)
        return execute(*args,**kwargs)
    def confirm(status,tool='',machine=m,**kwargs):
        return confirm_tool_state(machine.id,user.id,str(uuid4()),snapshot(machine.id)['revision'],status=status,tool_no=tool,reason='Vor Ort tatsächlich kontrolliert',**kwargs)
    def reject(call):
        before=snapshot(m.id);count=SetupOperation.query.count()
        try:call();assert False,'Unexpected accepted operation'
        except ValueError:db.session.rollback()
        assert snapshot(m.id)==before and SetupOperation.query.count()==count
    assert tool_snapshot(m.id)['status']=='unknown'
    n=TimeBooking.query.count()
    with patch('factoryos.modules.production.services.tool_mount_service.datetime') as clock:
        clock.utcnow.return_value=datetime.utcnow()-timedelta(hours=3)
        confirm('empty')
    assert TimeBooking.query.count()==n+1
    assert current_booking(m.id).process=='FREI' and current_booking(m.id).order_id is None
    reject(lambda:run('start',order_id=oa.id))
    # A late audit failure must roll inventory, operation and booking back together.
    from sqlalchemy import event
    from factoryos.core.models.change_log import ChangeLog
    before=snapshot(m.id);n=TimeBooking.query.count();ops=SetupOperation.query.count()
    def broken_audit(*args):raise RuntimeError('Synthetic audit failure')
    event.listen(ChangeLog,'before_insert',broken_audit)
    try:
        try:run('setup',tool_no='MOUNT-A');assert False
        except RuntimeError:db.session.rollback()
    finally:event.remove(ChangeLog,'before_insert',broken_audit)
    assert snapshot(m.id)==before and TimeBooking.query.count()==n and SetupOperation.query.count()==ops
    t=datetime.utcnow().replace(microsecond=0)-timedelta(hours=2)
    run('setup',order_id=oa.id,stamp=t)
    op=SetupOperation.query.filter_by(machine_id=m.id,outcome='active').one()
    assert op.kind=='RUEST' and op.tool_no=='MOUNT-A' and tool_snapshot(m.id)['status']=='unknown'
    reject(lambda:confirm('mounted','MOUNT-A'))
    run('fault',stamp=t+timedelta(minutes=10),comment='Kühlung unterbrochen')
    run('clear_fault',stamp=t+timedelta(minutes=15),comment='Kühlung kontrolliert')
    run('resume',stamp=t+timedelta(minutes=20))
    run('finish_setup',stamp=t+timedelta(minutes=30))
    assert op.outcome=='completed' and tool_snapshot(m.id)['status']=='mounted'
    times=operation_times(op);assert times==dict(work=1200,interruptions=600,total=1800),times
    reject(lambda:confirm('mounted','MOUNT-A',machine=other))
    reject(lambda:run('setup',machine=other,tool_no='MOUNT-A'))
    run('start',order_id=oa.id);active_id=current_booking(m.id).id
    reject(lambda:confirm('empty'))
    confirm('mounted','MOUNT-A')
    assert current_booking(m.id).id==active_id and current_booking(m.id).end_time is None
    run('stop',comment='Produktion erst später abschließen')
    assert tool_snapshot(m.id)['status']=='mounted' and current_booking(m.id).tool_no=='MOUNT-A'
    reject(lambda:run('start',order_id=ob.id))
    run('start',order_id=oa.id)
    mounted=copy.deepcopy(tool_snapshot(m.id))
    complete_order(oa.id,user.id,str(uuid4()),completion_context(oa)['revision'],good_qty='100',scrap_qty='0',confirmed=True,source='machine',machine_id=m.id)
    assert current_booking(m.id).process=='FREI' and tool_snapshot(m.id)==mounted
    # Dismount uses the actual tool, never the unrelated selected successor order.
    run('unsetup',order_id=ob.id)
    unmount=SetupOperation.query.filter_by(machine_id=m.id,outcome='active').one()
    assert unmount.tool_no=='MOUNT-A' and unmount.order_id is None
    reject(lambda:confirm('mounted','MOUNT-A',machine=other))
    run('finish_setup');assert tool_snapshot(m.id)['status']=='empty' and tool_snapshot(m.id)['tool_no'] is None
    assert unmount.outcome=='completed'
    run('setup',tool_no='MOUNT-B');run('pause')
    assert current_booking(m.id).process=='PAUSE' and SetupOperation.query.filter_by(machine_id=m.id,outcome='active').count()==1
    run('resume');run('stop',comment='Einbau abgebrochen, Teile fehlen')
    aborted=SetupOperation.query.filter_by(machine_id=m.id,outcome='aborted').one()
    assert tool_snapshot(m.id)['requires_confirmation']
    reject(lambda:run('start',order_id=ob.id));reject(lambda:run('setup',tool_no='MOUNT-B'))
    count=SetupOperation.query.count();confirm('mounted','MOUNT-B')
    assert SetupOperation.query.count()==count and aborted.outcome=='aborted'
    for call in (lambda:delete_tool(tb),lambda:update_tool(tb,{'tool_no':'RENAMED'},[],[])):
        reject(call)
    run('start',order_id=ob.id)
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    base='/production/machine/'+str(m.id)
    html=client.get(base+'/control').get_data(as_text=True)
    assert 'Gerüstet · Werkzeug MOUNT-B montiert' in html and 'Rüsthistorie' in html
    assert '20.0 Min' in html and '10.0 Min' in html
    page=client.get(base+'/tool-state');assert page.status_code==200
    text=page.get_data(as_text=True)
    fields={key:re.search(r'name="'+key+r'" value="([^"]+)"',text).group(1) for key in ('command_id','revision','access_csrf')}
    payload=dict(fields,status='mounted',tool_no='MOUNT-B',reason='Prüfung an laufender Maschine')
    no_csrf=dict(payload);no_csrf.pop('access_csrf')
    assert client.post(base+'/tool-state',data=no_csrf).status_code==400
    assert client.post(base+'/tool-state',data=payload).status_code==303
    assert client.post(base+'/tool-state',data=payload).status_code==303
    assert client.post(base+'/tool-state',data={**payload,'command_id':str(uuid4())}).status_code==409
    page=client.get('/production/booking');assert page.status_code==200,page.get_data(as_text=True)[:400]
    assert 'Gerüstet · Werkzeug MOUNT-B montiert' in page.get_data(as_text=True)
    porder=Order(order_no='MOUNT-PLAN',article='A001',tool_no='MOUNT-B',target_qty=100,cycle_time_s=30)
    db.session.add(porder);db.session.flush()
    db.session.add(ProductionPlanEntry(machine_id=other.id,order_id=porder.id,position=1,created_by_id=user.id,updated_by_id=user.id));db.session.commit()
    schedule=build_schedule();row=next(l for l in schedule['machines'] if l['machine'].id==other.id)['rows'][0]
    assert any('weiterhin auf MOUNT-1 montiert' in w for w in row['warnings']),row
    permission=Permission.query.filter_by(name='production.view').first()
    if not permission:permission=Permission(name='production.view');db.session.add(permission)
    reader=User(username='mount-reader',password_hash='unused',active=True,role=Role(name='mount-reader',active=True,permissions=[permission]));db.session.add(reader);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    assert denied.get(base+'/tool-state').status_code==403
print('PASS: independent tooling state, no false free on stop/completion, setup/teardown outcome, timed interruption segments, actual-tool dismount, abort reconciliation, inventory audit/replay/CSRF/ACL, double-mount prevention, tool identity preservation, timeline and plan warnings, non-destructive upgrade.')
