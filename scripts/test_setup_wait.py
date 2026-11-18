"""Setup decisions, genuine waiting time, historical evidence and read-only totals."""
import runpy,re,copy
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
fixture=runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import (TimeBooking,BookingIdleContext,MachineToolState,
    SetupOperation,MachineControlCommand,ProductionPlanEntry,QuantityReport,MachinePlanningSettings)
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking
from factoryos.modules.production.services.idle_context_service import idle_views,time_summary
from factoryos.modules.production.services.order_statistics import order_statistics
from factoryos.modules.production.services.planning_service import build_schedule
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.core.models.change_log import ChangeLog
from scripts.upgrade_setup_wait import run_upgrade

with app.app_context():
    admin=db.session.merge(fixture['user'])
    before=[(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()]
    grants={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    # Test the real additive migration, including an existing database without evidence.
    BookingIdleContext.__table__.drop(bind=db.engine);db.session.expire_all()
    run_upgrade(True);run_upgrade();run_upgrade()
    assert before==[(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()]
    assert grants=={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    machines=[Machine(machine_no='WAIT-'+str(i),machine_status='aktiv') for i in range(5)]
    tools=[Tool(tool_no='WAIT-'+str(i),name='Testwerkzeug',cavities=1) for i in range(5)]
    orders=[Order(order_no='WAIT-'+str(i),tool_no=tools[i].tool_no,target_qty=100,cycle_time_s=60) for i in range(5)]
    db.session.add_all([*machines,*tools,*orders]);db.session.flush()
    plan=ProductionPlanEntry(machine_id=machines[1].id,order_id=orders[1].id,position=1,state='queued',created_by_id=admin.id,updated_by_id=admin.id)
    plan_wait=ProductionPlanEntry(machine_id=machines[0].id,order_id=orders[0].id,position=1,state='queued',setup_minutes=30,created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add_all([plan,plan_wait]);db.session.commit()
    t=datetime(2026,11,2,8)
    def command(index,action,minutes,**kwargs):
        with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
            clock.utcnow.return_value=t+timedelta(minutes=minutes)
            return execute(machines[index].id,admin.id,action,str(uuid4()),snapshot(machines[index].id)['revision'],**kwargs)
    def reject(call):
        count=(TimeBooking.query.count(),MachineControlCommand.query.count(),BookingIdleContext.query.count())
        try:call()
        except ValueError:db.session.rollback()
        else:raise AssertionError('Unexpected accepted decision')
        assert count==(TimeBooking.query.count(),MachineControlCommand.query.count(),BookingIdleContext.query.count())
    command(0,'setup',0,order_id=orders[0].id)
    reject(lambda:command(0,'finish_setup',20,finish_mode='wait'))
    reject(lambda:command(0,'finish_setup',20,finish_mode='wait',wait_reason='other',comment='x'))
    command(0,'finish_setup',20,finish_mode='wait',wait_reason='material',comment='Granulat fehlt noch')
    waiting=current_booking(machines[0].id)
    assert waiting.process=='FREI' and waiting.order_id==orders[0].id and waiting.tool_no==tools[0].tool_no
    assert waiting.idle_context.reason_code=='material' and waiting.idle_context.tool_status=='mounted'
    assert idle_views([waiting],t+timedelta(minutes=24))[waiting.id]['hint']==''
    assert idle_views([waiting],t+timedelta(minutes=25))[waiting.id]['hint']
    lane=next(r for r in build_schedule(t+timedelta(minutes=30))['machines'] if r['machine'].id==machines[0].id)
    assert 'Material fehlt' in lane['error']
    db.session.add(MachinePlanningSettings(machine_id=machines[0].id,available_from=t+timedelta(minutes=35),availability_note='Material wird umgehend bereitgestellt'));db.session.commit()
    lane=next(r for r in build_schedule(t+timedelta(minutes=30))['machines'] if r['machine'].id==machines[0].id)
    assert lane['error'] is None and lane['rows'][0]['setup_start']==lane['rows'][0]['setup_end']
    reject(lambda:command(2,'start',30,order_id=orders[0].id))
    command(0,'record_wait',40,wait_reason='quality',comment='Material da; Erstteil wird geprüft')
    second=current_booking(machines[0].id)
    assert second.id!=waiting.id and waiting.end_time==second.start_time==t+timedelta(minutes=40)
    assert waiting.idle_context.reason_code=='material' and second.idle_context.reason_code=='quality'
    assert idle_views([second],t+timedelta(minutes=41))[second.id]['hint']
    command(0,'start',80,order_id=orders[0].id)
    production=current_booking(machines[0].id)
    assert production.process=='PROD' and second.end_time==production.start_time
    command(0,'stop',110,comment='Produktion für Zeitprüfung beendet')
    calendar=SimpleNamespace(week_start_day=0,week_start_time='04:30',week_end_day=5,week_end_time='06:00')
    stats=order_statistics(orders[0],t+timedelta(minutes=120),calendar,[])
    assert stats['waiting_seconds']==3600 and stats['working_seconds']==1800
    assert stats['runtime_difference'] is None and stats['good']==0
    rows=TimeBooking.query.filter_by(machine_id=machines[0].id).all()
    views=idle_views(rows,t+timedelta(minutes=120))
    summary=time_summary(rows,views,now=t+timedelta(minutes=120),calendar=calendar)
    totals={c['key']:c['seconds'] for c in summary['cards']}
    assert totals['RUEST']==1200 and totals['waiting']==4200 and totals['PROD']==1800
    assert dict(summary['reasons'])['Material fehlt']==1200
    assert dict(summary['reasons'])['QS-Freigabe fehlt']==2400
    assert dict(summary['reasons'])['Nicht erfasst']==600
    clipped=time_summary(rows,views,now=t+timedelta(minutes=120),start=t+timedelta(minutes=30),end=t+timedelta(minutes=60))
    assert dict(clipped['reasons'])=={'Material fehlt':600,'QS-Freigabe fehlt':1200}
    holiday=SimpleNamespace(start_at=t+timedelta(minutes=30),end_at=t+timedelta(minutes=60),title='Test')
    clipped=time_summary(rows,views,now=t+timedelta(minutes=120),start=t+timedelta(minutes=20),end=t+timedelta(minutes=80),calendar=calendar,exceptions=[holiday])
    assert sum(c['seconds'] for c in clipped['cards'])==1800
    # Atomic direct start: one command, no idle booking, exact common boundary and plan consumption.
    command(1,'setup',0,order_id=orders[1].id)
    setup=current_booking(machines[1].id);cmd=str(uuid4());rev=snapshot(machines[1].id)['revision']
    with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
        clock.utcnow.return_value=t+timedelta(minutes=15)
        receipt,replayed=execute(machines[1].id,admin.id,'finish_setup',cmd,rev,order_id=orders[1].id,finish_mode='start')
    prod=current_booking(machines[1].id)
    assert setup.end_time==prod.start_time and prod.process=='PROD' and prod.order_id==orders[1].id
    assert not TimeBooking.query.filter_by(machine_id=machines[1].id,process='FREI').count()
    assert plan.state=='started' and plan.started_booking_id==prod.id
    count=TimeBooking.query.count()
    assert execute(machines[1].id,admin.id,'finish_setup',cmd,rev,order_id=orders[1].id,finish_mode='start')[1]
    assert TimeBooking.query.count()==count
    # Failure after closing setup rolls stock, booking and operation back together.
    command(2,'setup',0,order_id=orders[2].id)
    state=copy.deepcopy(snapshot(machines[2].id))
    with patch('factoryos.modules.production.services.planning_service.consume_on_start',side_effect=ValueError('Synthetic late validation failure')):
        reject(lambda:command(2,'finish_setup',15,finish_mode='start',order_id=orders[2].id))
    assert snapshot(machines[2].id)==state
    # HTTP gates: old finish button only navigates, decisions need CSRF and actual-start confirmation.
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(admin.id);s['_fresh']=True
    path=f'/production/machine/{machines[2].id}/control/setup-finish'
    html=client.get(path).get_data(as_text=True)
    def hidden(name):return re.search(r'name="'+name+r'" value="([^"]*)"',html)[1]
    fields={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={**fields,'finish_mode':'start','order_id':orders[2].id}).status_code==400
    assert client.post(path,data={**fields,'finish_mode':'wait'}).status_code==400
    old_count=TimeBooking.query.count()
    assert client.post(f'/production/machine/{machines[2].id}/control',data={**fields,'action':'finish_setup'}).status_code==303
    assert TimeBooking.query.count()==old_count
    assert client.post(path,data={**fields,'finish_mode':'wait','wait_reason':'scheduled'}).status_code==303
    # A user who can finish setup cannot thereby gain production-start rights.
    permissions=[]
    for name in ('production.view','production.setup'):
        p=Permission.query.filter_by(name=name).first() or Permission(name=name)
        permissions.append(p)
    worker=User(username='wait-only',password_hash='unused',active=True,role=Role(name='wait-only',active=True,permissions=permissions))
    db.session.add(worker);db.session.commit()
    command(3,'setup',0,order_id=orders[3].id)
    restricted=app.test_client()
    with restricted.session_transaction() as s:s['_user_id']=str(worker.id);s['_fresh']=True
    restricted_path=f'/production/machine/{machines[3].id}/control/setup-finish'
    html=restricted.get(restricted_path).get_data(as_text=True)
    fields={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    assert restricted.post(restricted_path,data={**fields,'finish_mode':'start','production_confirmed':'yes','order_id':orders[3].id}).status_code==403
    assert restricted.post(restricted_path,data={**fields,'finish_mode':'wait','wait_reason':'staff'}).status_code==303
    # Historical evidence uses the original receipt, never the current machine stock.
    legacy=TimeBooking(user_id=admin.id,machine_id=machines[4].id,process='FREI',type='START',tool_no=tools[4].tool_no,start_time=t,end_time=t+timedelta(minutes=10))
    db.session.add(legacy);db.session.flush()
    def legacy_receipt(status):
        return MachineControlCommand(machine_id=machines[4].id,user_id=admin.id,source='app',action='finish_setup',command_id=str(uuid4()),payload_hash='test',before_state={},after_state={'active':[{'id':legacy.id,'process':'FREI'}],'tool_mount':{'status':status,'tool_no':tools[4].tool_no if status=='mounted' else None}})
    db.session.add(legacy_receipt('mounted'));db.session.commit()
    assert idle_views([legacy])[legacy.id]['tool_status']=='mounted'
    assert idle_views([legacy])[legacy.id]['reason']=='Nicht erfasst'
    db.session.add(legacy_receipt('empty'));db.session.commit()
    assert idle_views([legacy])[legacy.id]['tool_status']=='unknown'
    # Reads, filters, polling and HTTP output do not fabricate bookings or quantities.
    before=(TimeBooking.query.count(),QuantityReport.query.count(),ChangeLog.query.count(),BookingIdleContext.query.count())
    response=client.get('/production/booking/journal?q=WAIT-0&von=2026-11-02&bis=2026-11-02')
    assert response.status_code==200
    html=response.get_data(as_text=True)
    for text in ('Gerüstete Wartezeit','Material fehlt','QS-Freigabe fehlt','Abgerüsteter Leerlauf','Werkzeug'):assert text in html
    assert 'FREI · START' not in html
    assert client.get('/production/booking/journal?von=bad').status_code==400
    assert client.get(f'/orders/{orders[0].id}').status_code==200
    assert client.get('/production/booking').status_code==200
    with patch('factoryos.modules.production.services.idle_context_service.datetime') as clock:
        clock.utcnow.return_value=current_booking(machines[3].id).start_time+timedelta(minutes=6)
        assert client.get(f'/production/machine/{machines[3].id}/control/state').json['wait_hint']
    assert before==(TimeBooking.query.count(),QuantityReport.query.count(),ChangeLog.query.count(),BookingIdleContext.query.count())
    # Mounted inventory changes split idle records rather than relabeling old history.
    active=current_booking(machines[3].id);old_id=active.id
    confirm_tool_state(machines[3].id,admin.id,str(uuid4()),snapshot(machines[3].id)['revision'],status='empty',reason='Werkzeugbestand vor Ort korrigiert')
    new=current_booking(machines[3].id)
    assert new.id!=old_id and active.end_time==new.start_time
    assert active.idle_context.tool_status=='mounted' and new.idle_context.tool_status=='empty'
    # Open sampling uses MUSTER, while its existing readiness gate still applies.
    sample=SamplingOrder(order=orders[4],reason='new_tool',state='in_progress',machine_id=machines[4].id,tool_id=tools[4].id,created_by_id=admin.id)
    db.session.add(sample);db.session.commit()
    command(4,'setup',20,order_id=orders[4].id)
    sample.state='draft';db.session.commit()
    reject(lambda:command(4,'finish_setup',30,finish_mode='start',order_id=orders[4].id))
    sample.state='in_progress';db.session.commit()
    sample_path=f'/production/machine/{machines[4].id}/control/setup-finish'
    html=client.get(sample_path).get_data(as_text=True)
    fields={name:hidden(name) for name in ('access_csrf','command_id','revision')}
    payload={**fields,'finish_mode':'start','production_confirmed':'yes','order_id':orders[4].id}
    with patch('factoryos.modules.production.services.machine_control_service.datetime') as clock:
        clock.utcnow.return_value=t+timedelta(minutes=30)
        assert client.post(sample_path,data=payload).status_code==303
    assert client.post(sample_path,data=payload).status_code==303
    assert current_booking(machines[4].id).process=='MUSTER'
    # Both existing delete paths retain idle evidence in audit and remove its FK row.
    for repair in (False,True):
        removable=TimeBooking(user_id=admin.id,machine_id=machines[4].id,process='FREI',type='START',start_time=t-timedelta(hours=2),end_time=t-timedelta(hours=1),
            idle_context=BookingIdleContext(tool_status='empty',source='transition'))
        db.session.add(removable);db.session.commit();rid=removable.id
        delete_path=f'/production/booking/{rid}/'+('repair' if repair else 'review')
        html=client.get(delete_path).get_data(as_text=True)
        data={name:hidden(name) for name in ('access_csrf','revision')}
        data.update(action='delete',reason='Falsch erfasster synthetischer Leerlauf',intent='preview')
        assert client.post(delete_path,data=data).status_code==200
        data.update(intent='commit',confirm_delete='yes',acknowledge='yes')
        assert client.post(delete_path,data=data).status_code==303
        assert db.session.get(TimeBooking,rid) is None and db.session.get(BookingIdleContext,rid) is None
        logs=ChangeLog.query.filter_by(category='booking_admin_repair' if repair else 'booking_review').order_by(ChangeLog.id.desc()).first()
        payload=logs.changes['admin_repair' if repair else 'booking_review']
        assert payload['old']['idle_context']['tool_status']=='empty'

print('PASS: additive migration, direct setup/production boundary without idle and exact-once replay, atomic rollback, queued order consumption, explicit reason and reservations, reason changes preserve intervals, 5-minute hint, separate net/calendar/filter totals, historical evidence/unknowns, read-only HTTP/journal, CSRF/permissions, immutable inventory evidence, sampling start')
