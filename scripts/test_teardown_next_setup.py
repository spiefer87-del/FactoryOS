"""Atomic teardown->setup or empty idle, HTTP choice/ACL and retained history."""
import runpy,re,copy
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from sqlalchemy import event
fixture=runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,SetupOperation,MachineToolState,MachineControlCommand,BookingIdleContext,ProductionPlanEntry,QuantityReport
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state,operation_times
from factoryos.modules.production.services.idle_context_service import idle_views
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.core.models.change_log import ChangeLog

with app.app_context():
    admin=db.session.merge(fixture['user']);t=datetime(2026,11,2,8)
    machines=[];old_tools=[];new_tools=[];orders=[]
    for i in range(7):
        machine=Machine(machine_no='TEARDOWN-'+str(i),machine_status='aktiv')
        old=Tool(tool_no='TEARDOWN-OLD-'+str(i),name='Alt');new=Tool(tool_no='TEARDOWN-NEW-'+str(i),name='Neu')
        order=Order(order_no='TEARDOWN-ORDER-'+str(i),tool_no=new.tool_no,target_qty=100,cycle_time_s=30)
        db.session.add_all([machine,old,new,order]);machines.append(machine);old_tools.append(old);new_tools.append(new);orders.append(order)
    db.session.commit()
    def run(i,action,minutes=5,**kwargs):
        with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
            clock.utcnow.return_value=t+timedelta(minutes=minutes)
            return execute(machines[i].id,admin.id,action,str(uuid4()),snapshot(machines[i].id)['revision'],**kwargs)
    def prepare(i):
        with patch('factoryos.modules.production.services.tool_mount_service.datetime') as clock:
            clock.utcnow.return_value=t
            confirm_tool_state(machines[i].id,admin.id,str(uuid4()),snapshot(machines[i].id)['revision'],status='mounted',tool_no=old_tools[i].tool_no,reason='Bestand vor Ort geprüft')
        run(i,'unsetup')
        return current_booking(machines[i].id),SetupOperation.query.filter_by(machine_id=machines[i].id,outcome='active').one()
    def facts(i):
        return (copy.deepcopy(snapshot(machines[i].id)),TimeBooking.query.count(),SetupOperation.query.count(),BookingIdleContext.query.count(),MachineControlCommand.query.count())
    def reject(i,call):
        before=facts(i)
        try:call()
        except (ValueError,RuntimeError):db.session.rollback()
        else:raise AssertionError('Invalid transition accepted')
        assert facts(i)==before
    # Direct handover has exactly one new booking and two distinct operation records.
    old_booking,old_operation=prepare(0)
    plan=ProductionPlanEntry(machine_id=machines[0].id,order_id=orders[0].id,state='queued',position=1,created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add(plan);db.session.commit()
    before=TimeBooking.query.count();contexts=BookingIdleContext.query.count()
    revision=snapshot(machines[0].id)['revision'];cmd=str(uuid4())
    with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
        clock.utcnow.return_value=t+timedelta(minutes=20)
        receipt,_=execute(machines[0].id,admin.id,'finish_setup',cmd,revision,finish_mode='setup',tool_no=new_tools[0].tool_no,order_id=orders[0].id)
    new_booking=current_booking(machines[0].id)
    new_operation=SetupOperation.query.filter_by(machine_id=machines[0].id,outcome='active').one()
    assert old_booking.end_time==new_booking.start_time==old_operation.ended_at==new_operation.started_at==t+timedelta(minutes=20)
    assert old_operation.kind=='ABRUEST' and old_operation.outcome=='completed' and old_operation.tool_no==old_tools[0].tool_no
    assert new_operation.kind=='RUEST' and new_operation.tool_no==new_tools[0].tool_no and new_operation.start_booking_id==new_booking.id
    assert new_booking.process=='RUEST' and new_booking.order_id==orders[0].id and TimeBooking.query.count()==before+1
    assert BookingIdleContext.query.count()==contexts and new_booking.idle_context is None
    assert plan.state=='queued' and plan.started_booking_id is None and orders[0].status=='open'
    stock=db.session.get(MachineToolState,machines[0].id)
    assert stock.status=='unknown' and stock.tool_no==new_tools[0].tool_no and stock.requires_confirmation
    assert operation_times(old_operation)['work']==900
    assert execute(machines[0].id,admin.id,'finish_setup',cmd,revision,finish_mode='setup',tool_no=new_tools[0].tool_no,order_id=orders[0].id)[1]
    reject(0,lambda:execute(machines[0].id,admin.id,'finish_setup',cmd,revision,finish_mode='free'))
    # The existing setup-end decision still works after this handover.
    run(0,'finish_setup',40,finish_mode='wait',wait_reason='material')
    assert current_booking(machines[0].id).process=='FREI' and stock.status=='mounted'
    run(0,'start',50,order_id=orders[0].id)
    assert current_booking(machines[0].id).process=='PROD' and plan.state=='started'
    # Explicit empty idle has its own proven state and no invented next operation.
    b1,op1=prepare(1)
    run(1,'finish_setup',20,finish_mode='free')
    idle=current_booking(machines[1].id)
    assert idle.process=='FREI' and idle.tool_no is None and idle.order_id is None
    assert idle.start_time==b1.end_time==op1.ended_at and op1.outcome=='completed'
    assert idle.idle_context.tool_status=='empty' and idle_views([idle])[idle.id]['label']=='Abgerüstet · ohne Werkzeug'
    assert not SetupOperation.query.filter_by(machine_id=machines[1].id,outcome='active').count()
    # Invalid master/order/mount/state and late errors cannot partially end teardown.
    b2,op2=prepare(2)
    reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no='UNKNOWN'))
    reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no=new_tools[3].tool_no,order_id=orders[2].id))
    reject(2,lambda:run(2,'finish_setup',20,finish_mode='start',order_id=orders[2].id))
    reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no=new_tools[0].tool_no))
    with patch('factoryos.modules.production.services.tool_mount_service.assert_tool_available',side_effect=ValueError('Late tool validation failure')):
        reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no=new_tools[2].tool_no))
    def broken_audit(*args):raise RuntimeError('Late audit failure')
    event.listen(ChangeLog,'before_insert',broken_audit)
    try:reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no=new_tools[2].tool_no))
    finally:event.remove(ChangeLog,'before_insert',broken_audit)
    assert b2.end_time is None and op2.outcome=='active'
    machines[2].machine_status='inaktiv';db.session.commit()
    reject(2,lambda:run(2,'finish_setup',20,finish_mode='setup',tool_no=new_tools[2].tool_no))
    run(2,'finish_setup',20,finish_mode='free')
    # HTTP: deliberate selection, no-JS preview, acknowledgement and permission gates.
    b3,op3=prepare(3)
    def client_for(user):
        client=app.test_client()
        with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
        return client
    def permission(name):
        row=Permission.query.filter_by(name=name).first()
        if row is None:row=Permission(name=name);db.session.add(row);db.session.flush()
        return row
    view_right=permission('production.view');setup_right=permission('production.setup')
    worker=User(username='teardown-worker',password_hash='unused',active=True,role=Role(name='teardown-worker',active=True,permissions=[view_right,setup_right]))
    reader=User(username='teardown-reader',password_hash='unused',active=True,role=Role(name='teardown-reader',active=True,permissions=[view_right]))
    db.session.add_all([worker,reader]);db.session.commit();client=client_for(worker);denied=client_for(reader)
    base=f'/production/machine/{machines[3].id}/control';path=base+'/teardown-finish'
    assert app.test_client().get(path).status_code==302
    assert denied.get(path).status_code==403 and denied.post(path,data={}).status_code==403
    page=client.get(path);assert page.status_code==200;html=page.get_data(as_text=True)
    def hidden(name):return re.search(r'name="'+name+r'"[^>]*value="([^"]*)"',html)[1]
    fields={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    assert 'Direkt nächstes Werkzeug rüsten' in html and 'Ohne Werkzeug frei stehen lassen' in html
    assert path in client.get(base).get_data(as_text=True)
    before=facts(3)
    old=client.post(base,data={**fields,'action':'finish_setup'})
    assert old.status_code==303 and '/teardown-finish' in old.headers['Location'] and facts(3)==before
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={**fields,'finish_mode':'setup','tool_no':new_tools[3].tool_no,'order_id':orders[3].id}).status_code==400
    assert facts(3)==before
    preview=client.post(path,data={**fields,'action':'preview_selection','order_id':orders[3].id})
    assert preview.status_code==200 and f'value="{new_tools[3].tool_no}"' in preview.get_data(as_text=True)
    assert facts(3)==before
    payload={**fields,'finish_mode':'setup','tool_no':new_tools[3].tool_no,'tool_confirmed':'yes','tool_confirmation_no':new_tools[3].tool_no,'order_id':orders[3].id}
    with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
        clock.utcnow.return_value=t+timedelta(minutes=20)
        assert client.post(path,data=payload).status_code==303
    assert client.post(path,data=payload).status_code==303
    assert current_booking(machines[3].id).process=='RUEST'  # no production.start right needed
    log=ChangeLog.query.filter_by(entity_type='machine',entity_id=machines[3].id).order_by(ChangeLog.id.desc()).first()
    decision=log.changes['setup_decision']['new']
    assert decision['decision']=='Direkt nächstes Werkzeug rüsten' and decision['previous_tool_no']==old_tools[3].tool_no and decision['tool_no']==new_tools[3].tool_no
    assert log.user_id==worker.id
    # Free choice ignores incomplete next-tool fields; stale and active conflicts fail.
    b4,op4=prepare(4);admin_client=client_for(admin);p4=f'/production/machine/{machines[4].id}/control/teardown-finish'
    html=admin_client.get(p4).get_data(as_text=True);fields4={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    stale={**fields4,'finish_mode':'free','tool_no':'UNKNOWN','order_id':'bad'}
    duplicate=TimeBooking(user_id=admin.id,machine_id=machines[4].id,process='PAUSE',type='START',start_time=t+timedelta(minutes=10))
    db.session.add(duplicate);db.session.commit()
    assert admin_client.post(p4,data=stale).status_code==409
    assert b4.end_time is None and op4.outcome=='active'
    db.session.delete(duplicate);db.session.commit()
    html=admin_client.get(p4).get_data(as_text=True);fields4={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    assert admin_client.post(p4,data={**fields4,'finish_mode':'free','tool_no':'UNKNOWN','order_id':'bad'}).status_code==303
    assert current_booking(machines[4].id).process=='FREI'
    # Prepared sampling follows its existing assignment gate; manual tool-only setup is allowed.
    b5,op5=prepare(5)
    sample=SamplingOrder(order=orders[5],reason='new_tool',state='draft',tool_id=new_tools[5].id,machine_id=machines[5].id,created_by_id=admin.id)
    db.session.add(sample);db.session.commit()
    reject(5,lambda:run(5,'finish_setup',20,finish_mode='setup',tool_no=new_tools[5].tool_no,order_id=orders[5].id))
    sample.state='in_progress';db.session.commit()
    run(5,'finish_setup',20,finish_mode='setup',tool_no=new_tools[5].tool_no,order_id=orders[5].id)
    assert current_booking(machines[5].id).process=='RUEST' and sample.state=='in_progress'
    b6,op6=prepare(6)
    run(6,'finish_setup',20,finish_mode='setup',tool_no=new_tools[6].tool_no)
    assert current_booking(machines[6].id).order_id is None
    # Read-only journal/timeline preserve old entries; no cleanup or quantity fabrication.
    count=QuantityReport.query.count();records=[(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()]
    assert admin_client.get('/production/booking/journal').status_code==200
    assert admin_client.get('/production/booking').status_code==200
    assert records==[(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()] and QuantityReport.query.count()==count

print('PASS: atomic teardown-to-setup boundary without idle, separate tools/operations and no production start, explicit empty state, replay/conflicting UUID, rollback after late tool/audit failures, queue retained, HTTP/no-JS/CSRF/ACL, tool acknowledgement, master/assignment/reservation/stale/inactive guards, sampling/manual setup, readable audit and preserved historical bookings')
