"""Synthetic warehouse lifecycle. Never production data."""
import runpy
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.inventory.models import *
from factoryos.modules.inventory.service import execute,revision,balance,available,pending
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import QuantityReport
from scripts.upgrade_inventory import run_upgrade

with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article']);machine=db.session.merge(fixture['machine'])
    from scripts.upgrade_inventory import MODELS
    for model in reversed(MODELS):model.__table__.drop(bind=db.engine,checkfirst=True)
    run_upgrade(True);run_upgrade();run_upgrade()
    order=Order(order_no='WH-TEST',article=article.article_no,target_qty=100,cycle_time_s=30)
    db.session.add(order);db.session.flush()
    db.session.add(QuantityReport(order_id=order.id,machine_id=machine.id,user_id=user.id,good_qty=100,scrap_qty=5));db.session.commit()
    def run(action,**data):
        result=execute(user.id,action,str(uuid4()),revision(),dict(confirmed='yes',reason='Testbeleg fachlich geprüft',**{k:str(v) for k,v in data.items()}));return result[0]
    def reject(action,**data):
        count=WarehouseEvent.query.count()
        try:run(action,**data);assert False,'Unexpected success '+action
        except ValueError:db.session.rollback()
        assert WarehouseEvent.query.count()==count
    run('location',code='A-01',description='Fertigware');run('location',code='B-01',description='Versand')
    p,q=WarehouseLocation.query.order_by(WarehouseLocation.id).all()
    reject('transfer',order_id=order.id,article_id=article.id,batch='TEST',quantity=101)
    run('transfer',order_id=order.id,article_id=article.id,batch='TEST',quantity=100)
    lot=WarehouseLot.query.one();assert pending(lot)==100
    reject('transfer',order_id=order.id,article_id=article.id,batch='TEST2',quantity=1)
    receipt=run('receive',lot_id=lot.id,quantity=80,destination_id=p.id)
    run('reject',lot_id=lot.id,quantity=5);assert pending(lot)==15 and balance(lot.id,p.id,'blocked')==80
    reject('reserve',lot_id=lot.id,location_id=p.id,quantity=1,reference='Kunde 1')
    run('release',lot_id=lot.id,location_id=p.id,quantity=70)
    run('reserve',lot_id=lot.id,location_id=p.id,quantity=50,reference='Kunde 1 / LS-001');r=WarehouseReservation.query.one()
    assert available(lot.id,p.id)==20
    reject('scrap',lot_id=lot.id,location_id=p.id,status='free',quantity=21)
    reject('ship',reservation_id=r.id,quantity=10)
    run('pick',reservation_id=r.id);shipment=run('ship',reservation_id=r.id,quantity=20)
    assert r.remaining==30 and balance(lot.id,p.id,'free')==50
    run('unreserve',reservation_id=r.id,quantity=10);assert r.remaining==20
    run('ship',reservation_id=r.id,quantity=20);assert r.remaining==0
    run('return',event_id=shipment.id,quantity=5,destination_id=q.id)
    reject('return',event_id=shipment.id,quantity=16,destination_id=q.id)
    scrap=run('scrap',lot_id=lot.id,location_id=p.id,status='blocked',quantity=3)
    run('reverse',event_id=scrap.id,quantity=3);reject('reverse',event_id=scrap.id,quantity=3)
    move=run('move',lot_id=lot.id,location_id=p.id,status='free',quantity=10,destination_id=q.id)
    run('reverse',event_id=move.id,quantity=10)
    reject('reverse',event_id=receipt.id,quantity=80)
    data=dict(confirmed='yes',reason='Doppelklick-Test',lot_id=str(lot.id),quantity='5',destination_id=str(q.id));cmd=str(uuid4());rev=revision()
    first,replayed=execute(user.id,'receive',cmd,rev,data);second,replayed=execute(user.id,'receive',cmd,rev,data)
    assert replayed and first.id==second.id and pending(lot)==10
    try:execute(user.id,'receive',str(uuid4()),rev,data);assert False
    except ValueError:db.session.rollback()
    try:db.session.execute(text('DELETE FROM warehouse_events'));db.session.commit();assert False
    except Exception:db.session.rollback()
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    for view in ('overview','incoming','stock','outbound','locations','journal'):
        page=client.get('/warehouse/?view='+view);assert page.status_code==200,page.get_data(as_text=True)[:500]
    page=client.get('/warehouse/receive');assert page.status_code==200
    assert client.post('/warehouse/receive',data={}).status_code==400
    from factoryos.modules.inventory.service import protect_final_total
    try:protect_final_total(order.id,99);assert False
    except ValueError:pass
    assert client.get('/warehouse/journal/'+str(receipt.id)).status_code==200
    # An unused opening can be reversed without pretending it was scrap.
    opening=run('opening',article_id=article.id,batch='COUNT-CORRECTION',quantity=3,destination_id=p.id)
    run('reverse',event_id=opening.id,quantity=3)
    assert balance(opening.lot_id,p.id,'blocked')==0
    order2=Order(order_no='WH-CANCEL',article=article.article_no,target_qty=10,cycle_time_s=30);db.session.add(order2);db.session.flush()
    db.session.add(QuantityReport(order_id=order2.id,machine_id=machine.id,user_id=user.id,good_qty=10,scrap_qty=0));db.session.commit()
    first_transfer=run('transfer',order_id=order2.id,article_id=article.id,batch='MISTAKE',quantity=10)
    run('cancel',lot_id=first_transfer.lot_id,quantity=10)
    run('transfer',order_id=order2.id,article_id=article.id,batch='CORRECT',quantity=10)
    # Transaction failure after stock lines were flushed must undo everything.
    from sqlalchemy import event as sa_event
    state_before=revision();count_before=WarehouseEvent.query.count();stock_before=balance(lot.id,p.id,'blocked')
    def fail(*args):raise RuntimeError('Synthetic commit failure')
    sa_event.listen(WarehouseLock,'before_update',fail)
    try:
        try:run('scrap',lot_id=lot.id,location_id=p.id,status='blocked',quantity=1);assert False
        except RuntimeError:db.session.rollback()
    finally:sa_event.remove(WarehouseLock,'before_update',fail)
    assert revision()==state_before and WarehouseEvent.query.count()==count_before and balance(lot.id,p.id,'blocked')==stock_before
    from factoryos.models.user import User
    from factoryos.modules.admin.roles.models import Role
    from factoryos.modules.admin.permissions.models import Permission
    reader=User(username='warehouse-reader',password_hash='unused',active=True,role=Role(name='warehouse-reader',active=True,permissions=[Permission.query.filter_by(name='inventory.view').one()]));db.session.add(reader);db.session.commit()
    limited=app.test_client()
    with limited.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    assert limited.get('/warehouse/').status_code==200
    for action in ('location','transfer','receive','release','scrap','ship','reverse'):
        assert limited.get('/warehouse/'+action).status_code==403
        assert limited.post('/warehouse/'+action,data={}).status_code==403
print('PASS: additive upgrade twice; confirmed-good bound; no forecast stock; partial receipt and pre-stock scrap; quarantine/release; reservation protection; pick/partial ship/cancel/return; stock scrap/reversal; double reverse; exact-once UUID; stale token; immutable DB journal; pages and CSRF.')
