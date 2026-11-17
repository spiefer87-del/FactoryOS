import runpy
from pathlib import Path
from datetime import datetime,timedelta
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.production.models import TimeBooking,SetupOperation,MachineToolState,MachineControlState
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.order_statistics import local_time
from factoryos.modules.booking_review.admin_repair import revision

with app.app_context():
    user=db.session.merge(fixture['user']);tool=db.session.merge(fixture['tool'])
    machine=Machine(machine_no='ADMIN-REPAIR',machine_status='aktiv');db.session.add(machine);db.session.flush()
    now=datetime.utcnow().replace(microsecond=0)
    begin=now-timedelta(days=3)
    row=TimeBooking(user_id=user.id,machine_id=machine.id,tool_no=tool.tool_no,type='START',process='RUEST',start_time=begin,end_time=begin+timedelta(seconds=11))
    stock=MachineToolState(machine_id=machine.id,status='mounted',tool_no=tool.tool_no,updated_by_id=user.id,updated_at=now)
    control=MachineControlState(machine_id=machine.id,version=1)
    db.session.add_all([row,stock,control]);db.session.flush()
    op=SetupOperation(machine_id=machine.id,tool_no=tool.tool_no,kind='RUEST',outcome='completed',start_booking_id=row.id,started_by_id=user.id,started_at=begin,ended_at=begin+timedelta(seconds=30))
    db.session.add(op);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
    path=f'/production/booking/{row.id}/repair'
    assert client.get('/production/booking/journal?q=ADMIN-REPAIR').status_code==200
    assert client.get(path).status_code==200
    with client.session_transaction() as s:csrf=s['access_csrf']
    stamp=lambda value:local_time(value).strftime('%Y-%m-%dT%H:%M:%S')
    data=dict(action='move',start=stamp(begin-timedelta(days=1)),end=stamp(begin-timedelta(days=1)+timedelta(seconds=11)),reason='Fehleingabe aus Testphase bereinigen',revision=revision(row),access_csrf=csrf)
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==400
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==303
    assert row.start_time==begin-timedelta(days=1) and op.ended_at==row.end_time and op.started_at==row.start_time
    assert stock.status=='mounted' and not stock.requires_confirmation
    reader=User(username='not-system-admin',active=True,password_hash='unused',role=Role(name='not-system-admin',active=True,permissions=[Permission(name='production.view'),Permission(name='production.delete_booking')]))
    db.session.add(reader);db.session.commit();denied=app.test_client()
    with denied.session_transaction() as s:s['_user_id']=str(reader.id);s['_fresh']=True;s['access_csrf']='reader'
    assert denied.get('/production/booking/journal').status_code==200
    assert denied.get(path).status_code==403
    assert denied.post(path,data={**data,'access_csrf':'reader','intent':'preview'}).status_code==403
    data.update(action='delete',revision=revision(row))
    assert client.post(path,data={**data,'access_csrf':'bad','intent':'preview'}).status_code==400
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit'}).status_code==400
    row_id=row.id;op_id=op.id
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==303
    assert db.session.get(TimeBooking,row_id) is None and db.session.get(SetupOperation,op_id) is None
    assert stock.status=='mounted'
    audit=ChangeLog.query.filter_by(category='booking_admin_repair').order_by(ChangeLog.id.desc()).first()
    assert audit.changes['admin_repair']['old']['id']==row_id
    assert client.get('/production/booking/journal?q=DOES-NOT-EXIST').status_code==200
    active=TimeBooking(user_id=user.id,machine_id=machine.id,process='RUEST',tool_no=tool.tool_no,type='START',start_time=begin)
    db.session.add(active);db.session.flush()
    open_op=SetupOperation(machine_id=machine.id,tool_no=tool.tool_no,kind='RUEST',outcome='active',start_booking_id=active.id,started_by_id=user.id,started_at=begin)
    db.session.add(open_op);db.session.commit()
    path=f'/production/booking/{active.id}/repair'
    data.update(action='move',start=stamp(begin),end=stamp(begin+timedelta(seconds=60)),revision=revision(active))
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==303
    assert open_op.outcome=='aborted' and open_op.ended_at==active.end_time and stock.requires_confirmation
    from factoryos.modules.orders.models import Order
    from factoryos.modules.production.models import QuantityReport,ProductionPlanEntry
    from sqlalchemy import text
    closed_order=Order(order_no='ADMIN-CLOSED',status='fertig');db.session.add(closed_order);db.session.flush()
    historical=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=closed_order.id,type='START',process='WARTUNG',start_time=begin-timedelta(days=5),end_time=begin-timedelta(days=5,hours=-1))
    db.session.add(historical);db.session.add(QuantityReport(user_id=user.id,machine_id=machine.id,order_id=closed_order.id,good_qty=5,scrap_qty=1));db.session.commit()
    path=f'/production/booking/{historical.id}/repair'
    data.update(action='move',start=stamp(begin-timedelta(days=6)),end=stamp(begin-timedelta(days=6,hours=-1)),revision=revision(historical))
    response=client.post(path,data={**data,'intent':'preview'})
    assert response.status_code==200 and 'Mengen' in response.get_data(as_text=True)
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==303
    assert closed_order.status=='fertig' and QuantityReport.query.filter_by(order_id=closed_order.id).one().good_qty==5
    entry=ProductionPlanEntry(machine_id=machine.id,order_id=closed_order.id,position=0,state='started',created_by_id=user.id,updated_by_id=user.id,started_booking_id=historical.id)
    db.session.add(entry);db.session.commit()
    db.session.execute(text('CREATE TABLE admin_unknown_ref (id INTEGER PRIMARY KEY, booking_id INTEGER REFERENCES time_bookings(id))'))
    db.session.execute(text('INSERT INTO admin_unknown_ref (booking_id) VALUES (:id)'),{'id':historical.id});db.session.commit()
    data.update(action='delete',revision=revision(historical))
    assert client.post(path,data={**data,'intent':'preview'}).status_code==400
    db.session.execute(text('DROP TABLE admin_unknown_ref'));db.session.commit()
    data['revision']=revision(historical)
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit','acknowledge':'yes'}).status_code==303
    assert entry.started_booking_id is None and entry.state=='started' and closed_order.status=='fertig'
print('PASS: exact mismatched-end-time case; journal/search; strict admin ACL; CSRF; preview and acknowledgment; paired correction/deletion; audit snapshots; preserved physical stock; explicit closure of active setup requires stock confirmation')
