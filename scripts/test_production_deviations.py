import runpy
from pathlib import Path
from datetime import datetime,timedelta
from types import SimpleNamespace
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking,QuantityReport
from factoryos.modules.production.services.order_statistics import order_statistics
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from factoryos.modules.production_deviations.models import ProductionDeviationConfirmation as Confirmation
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from scripts.upgrade_production_deviations import run_upgrade

with app.app_context():
    run_upgrade();run_upgrade()
    user=db.session.merge(fixture['user']);tool=Tool(tool_no='DEV-TOOL',name='Dev',cavities=1);machine=Machine(machine_no='DEV-MACHINE',machine_status='aktiv')
    order=Order(order_no='DEV-ORDER',status='running',tool_no=tool.tool_no,target_qty=10,cycle_time_s=60)
    db.session.add_all([tool,machine,order]);db.session.flush()
    now=datetime.utcnow().replace(microsecond=0)
    booking=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=order.id,tool_no=tool.tool_no,type='START',process='PROD',start_time=now-timedelta(hours=5))
    db.session.add(booking);db.session.commit()
    calendar=SimpleNamespace(week_start_day=0,week_start_time='00:00',week_end_day=6,week_end_time='23:59')
    stats=order_statistics(order,now,calendar,[])
    assert stats['deviation']['kind']=='overdue' and stats['eta'] is None and stats['good']==0
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
    path=f'/production/deviations/order/{order.id}'
    response=client.get(path);assert response.status_code==200
    with client.session_transaction() as s:csrf=s['access_csrf']
    actual=order_statistics(order);assert actual['deviation']['kind']=='overdue'
    data=dict(access_csrf=csrf,signature=actual['deviation']['signature'],category='Mengenmeldung fehlt oder verspätet',reason='Mengen noch nicht gemeldet, Prozess wird geprüft.',confirmed='yes')
    assert client.post(path,data={**data,'access_csrf':'bad'}).status_code==400
    assert client.post(path,data={**data,'reason':'kurz'}).status_code==422
    assert client.post(path,data=data).status_code==303
    assert Confirmation.query.count()==1 and order_statistics(order)['deviation']['confirmation']
    timeline=get_machine_timeline('24h',now=now)
    # The HTTP rendering also exercises the colored bar and machine warning.
    html=client.get('/production/booking').get_data(as_text=True);assert 'deviation-overdue' in html and 'Soll-Laufzeit überschritten' in html
    order.cycle_time_s=61;db.session.commit()
    assert client.post(path,data=data).status_code==409
    assert order_statistics(order)['deviation']['confirmation'] is None
    reader=User(username='deviation-reader',password_hash='unused',active=True,role=Role(name='deviation-reader',active=True,permissions=[Permission(name='production.view')]))
    db.session.add(reader);db.session.commit();denied=app.test_client()
    with denied.session_transaction() as s:s['_user_id']=str(reader.id);s['_fresh']=True
    assert denied.get(path).status_code==403 and denied.post(path,data=data).status_code==403
    booking.start_time=now-timedelta(seconds=300);booking.end_time=now;order.status='finished';order.cycle_time_s=60
    db.session.add(QuantityReport(user_id=user.id,order_id=order.id,machine_id=machine.id,good_qty=10,scrap_qty=0));db.session.commit()
    assert order_statistics(order,now,calendar,[])['deviation']['kind']=='faster'
    booking.start_time=now-timedelta(seconds=1200);db.session.commit()
    assert order_statistics(order,now,calendar,[])['deviation']['kind']=='slower'
    assert Confirmation.query.count()==1
print('PASS: overdue without fabricated quantities/actual cycles, stable no-ETA-zero, colored timeline and order panel, reasons/CSRF/ACL, persisted snapshots, invalidated confirmation on source change, faster/slower completed quantity comparison, history retention; upgrade twice')
