"""Isolated integration: machine/office close, quantities, safety, replay, ACL."""
import copy
import re
import runpy
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_machine_control.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import (OrderCompletion,TimeBooking,QuantityReport,ProductionPlanEntry,
    MachineControlCommand,MachineControlState)
from factoryos.modules.production.services.order_completion_service import complete_order,completion_context
from factoryos.modules.production.services.machine_control_service import execute,snapshot,ControlConflict,ControlDenied,current_booking
from factoryos.modules.production.services.order_statistics import order_statistics
from scripts.upgrade_order_completion import run_upgrade

with app.app_context():
    admin=db.session.merge(fixture['admin'])
    before=Order.query.count();grants={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    run_upgrade(True);run_upgrade();run_upgrade()
    assert Order.query.count()==before and grants=={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    machines=[Machine(machine_no='END-'+str(i),machine_status='aktiv') for i in range(5)]
    orders=[Order(order_no='END-'+str(i),article='A001',article_name='Artikel 1',tool_no='W001',target_qty=100,cycle_time_s=30) for i in range(8)]
    db.session.add_all([*machines,*orders]);db.session.commit()
    def start(order,machine):return execute(machine.id,admin.id,'start',str(uuid4()),snapshot(machine.id)['revision'],order_id=order.id)
    def close(order,**kw):
        args=dict(good_qty='100',scrap_qty='0',confirmed=True)
        args.update(kw)
        return complete_order(order.id,admin.id,str(uuid4()),completion_context(order)['revision'],**args)
    def reject(order,**kw):
        status=order.status;n=OrderCompletion.query.count();bookings=TimeBooking.query.count()
        try:close(order,**kw);assert False,'Unexpected completion'
        except ValueError:db.session.rollback()
        assert order.status==status and OrderCompletion.query.count()==n and TimeBooking.query.count()==bookings
    order=orders[0];machine=machines[0]
    first_plan=ProductionPlanEntry(machine_id=machine.id,order_id=order.id,position=1,state='queued',created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add(first_plan);db.session.commit();start(order,machine)
    assert first_plan.state=='started'
    db.session.add(QuantityReport(order_id=order.id,machine_id=machine.id,user_id=admin.id,good_qty=20,scrap_qty=2));db.session.commit()
    reject(order,good_qty='19');reject(order,scrap_qty='1');reject(order,confirmed=False,scrap_qty='2')
    reject(order,good_qty='99',scrap_qty='2');reject(order,good_qty='NaN');reject(order,good_qty='1.5')
    rev=completion_context(order)['revision'];cmd=str(uuid4());n=TimeBooking.query.count()
    result,replayed=complete_order(order.id,admin.id,cmd,rev,good_qty='100',scrap_qty='3',confirmed=True,source='machine',machine_id=machine.id)
    assert not replayed and order.status=='finished'
    assert first_plan.state=='completed'
    assert current_booking(machine.id).process=='FREI' and current_booking(machine.id).order_id is None
    assert TimeBooking.query.filter_by(order_id=order.id,end_time=None).count()==0
    assert MachineControlState.query.filter_by(resume_order_id=order.id).count()==0
    assert QuantityReport.query.filter_by(order_id=order.id).count()==1 # no additive double count
    stats=order_statistics(order);assert stats['good']==100 and stats['scrap']==3 and stats['eta'] is None
    again,replayed=complete_order(order.id,admin.id,cmd,rev,good_qty='100',scrap_qty='3',confirmed=True,source='machine',machine_id=machine.id)
    assert replayed and again.id==result.id and TimeBooking.query.count()==n+1
    try:complete_order(order.id,admin.id,cmd,rev,good_qty='101',scrap_qty='3',confirmed=True,source='machine',machine_id=machine.id);assert False
    except ControlConflict:db.session.rollback()
    reject(order)
    # Office can close a never-started or previously stopped/queued order.
    plan=ProductionPlanEntry(machine_id=machines[1].id,order_id=orders[1].id,position=1,state='queued',created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add(plan);db.session.commit();bookings=TimeBooking.query.count()
    close(orders[1],good_qty='80',reason='Restmenge entfällt nach Kundenfreigabe',short_confirmed=True)
    assert plan.state=='completed' and TimeBooking.query.count()==bookings
    assert order_statistics(orders[1])['good']==80
    start(orders[2],machines[1]);execute(machines[1].id,admin.id,'stop',str(uuid4()),snapshot(machines[1].id)['revision'],comment='Später im Büro abschließen')
    free_id=current_booking(machines[1].id).id;close(orders[2]);assert current_booking(machines[1].id).id==free_id
    # A fault is not cleared as a side effect, and stale quantity snapshots fail.
    start(orders[3],machines[2]);execute(machines[2].id,admin.id,'fault',str(uuid4()),snapshot(machines[2].id)['revision'],comment='Wasser fehlt')
    reject(orders[3]);assert current_booking(machines[2].id).process=='STOERUNG'
    rev=completion_context(orders[4])['revision'];orders[4].target_qty=101;db.session.commit()
    try:complete_order(orders[4].id,admin.id,str(uuid4()),rev,good_qty='101',scrap_qty='0',confirmed=True);assert False
    except ControlConflict:db.session.rollback()
    reject(orders[4],source='machine',machine_id=machines[0].id,good_qty='101')
    # Route tests: exact menu flow, office editing link, CSRF, rights and no restart.
    start(orders[5],machines[3])
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(admin.id);session['_fresh']=True
    panel=f'/production/machine/{machines[3].id}/control'
    html=client.get(panel+'?embedded=1').get_data(as_text=True)
    assert '/control/stop?' in html and 'Stoppen oder Auftrag abschließen' in html
    stop=client.get(panel+'/stop?embedded=1');assert stop.status_code==200
    assert 'Nur stoppen' in stop.get_data(as_text=True) and 'Auftrag abschließen' in stop.get_data(as_text=True)
    page=client.get(panel+'/complete-order?embedded=1');assert page.status_code==200
    text=page.get_data(as_text=True)
    def hidden(name):return re.search(r'name="'+name+r'" value="([^"]*)"',text).group(1)
    payload=dict(order_id=orders[5].id,command_id=hidden('command_id'),revision=hidden('revision'),good_qty='100',scrap_qty='0',confirmed='yes')
    assert client.post(panel+'/complete-order?embedded=1',data=payload).status_code==400
    payload['access_csrf']=hidden('access_csrf')
    response=client.post(panel+'/complete-order?embedded=1',data=payload);assert response.status_code==303,response.get_data(as_text=True)
    assert client.post(panel+'/complete-order?embedded=1',data=payload).status_code==303
    assert current_booking(machines[3].id).process=='FREI'
    assert 'Auftrag abgeschlossen' in client.get('/orders/'+str(orders[5].id)).get_data(as_text=True)
    edit=client.get('/orders/edit/'+str(orders[6].id));assert edit.status_code==200
    assert 'Endmengen erfassen' in edit.get_data(as_text=True)
    assert client.get('/orders/'+str(orders[6].id)+'/complete').status_code==200
    user=User(username='no-close',password_hash='unused',active=True,role=Role(name='no-close',active=True,permissions=[]))
    db.session.add(user);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    assert denied.get('/orders/'+str(orders[6].id)+'/complete').status_code==403
    assert denied.post(panel+'/complete-order',data=payload).status_code==403
    # Separate floor/office scopes cannot be substituted for one another.
    user.role.permissions=[Permission.query.filter_by(name='production.complete_order').one()];db.session.commit()
    try:complete_order(orders[6].id,user.id,str(uuid4()),completion_context(orders[6])['revision'],good_qty='100',scrap_qty='0',confirmed=True);assert False
    except ControlDenied:db.session.rollback()
    start(orders[7],machines[4]);execute(machines[4].id,admin.id,'pause',str(uuid4()),snapshot(machines[4].id)['revision'])
    complete_order(orders[7].id,user.id,str(uuid4()),completion_context(orders[7])['revision'],
        good_qty='100',scrap_qty='0',confirmed=True,source='machine',machine_id=machines[4].id)
    assert orders[7].status=='finished' and current_booking(machines[4].id).process=='FREI'
    start(orders[4],machines[4]);close(orders[4],good_qty='101')
    assert orders[4].status=='finished' and current_booking(machines[4].id).process=='FREI'
    orders[6].is_project=True;db.session.commit();reject(orders[6]);orders[6].is_project=False;db.session.commit()
    sample=Order.query.filter(Order.sampling.has()).first()
    if sample:reject(sample)
    # Preserve immutable offline completion against delete and edit/reopen routes.
    token=payload['access_csrf']
    assert client.post('/orders/edit/'+str(orders[1].id),data=dict(access_csrf=token,status='open')).status_code==400
    client.post('/orders/delete/'+str(orders[1].id),data=dict(access_csrf=token))
    assert db.session.get(Order,orders[1].id) and OrderCompletion.query.filter_by(order_id=orders[1].id).count()==1
print('PASS: upgrade preservation, machine stop/finish menu and office path, final totals not additive, atomic booking/state/queue closure, explicit shortfall, stale/invalid/CSRF/ACL rejection, UUID replay, immutable completion, no automatic restart or fault acknowledgement.')
