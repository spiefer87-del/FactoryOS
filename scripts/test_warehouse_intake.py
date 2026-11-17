"""Atomic quick-intake regression; isolated SQLite fixtures only."""
import runpy,re
from pathlib import Path
from uuid import uuid4
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_inventory.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import QuantityReport
from factoryos.modules.inventory.models import WarehouseLot,WarehouseEvent
from factoryos.modules.inventory.service import quick_intake,revision,balance,pending

with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article']);machine=db.session.merge(fixture['machine']);place=db.session.merge(fixture['p'])
    order=Order(order_no='QUICK-500',article=article.article_no,target_qty=500,cycle_time_s=30);db.session.add(order);db.session.flush()
    db.session.add(QuantityReport(order_id=order.id,machine_id=machine.id,user_id=user.id,good_qty=500,scrap_qty=5));db.session.commit()
    data=dict(quantity='200',batch='REAL-LOT',reason='Übergabe und Empfang vor Ort bestätigt',confirmed='yes',mode='receive',destination_id=str(place.id))
    cmd=str(uuid4());rev=revision();first,replay=quick_intake(user.id,order.id,cmd,rev,data)
    assert not replay and balance(first.lot_id,place.id,'blocked')==200 and pending(db.session.get(WarehouseLot,first.lot_id))==0
    first2,replay=quick_intake(user.id,order.id,cmd,rev,data);assert replay and first.id==first2.id
    assert WarehouseEvent.query.filter_by(lot_id=first.lot_id).count()==2
    counts=(WarehouseLot.query.count(),WarehouseEvent.query.count());rev=revision()
    try:quick_intake(user.id,order.id,str(uuid4()),rev,{**data,'destination_id':'999999'});assert False
    except ValueError:db.session.rollback()
    assert counts==(WarehouseLot.query.count(),WarehouseEvent.query.count()) and revision()==rev
    try:quick_intake(user.id,order.id,str(uuid4()),rev,{**data,'quantity':'301'});assert False
    except ValueError:db.session.rollback()
    reader=db.session.merge(fixture['reader'])
    try:quick_intake(reader.id,order.id,str(uuid4()),revision(),data);assert False
    except PermissionError:db.session.rollback()
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    count=WarehouseEvent.query.count()
    html=client.get('/warehouse/?view=incoming').get_data(as_text=True)
    assert f'data-intake-url="/warehouse/intake/{order.id}"' in html and 'warehouse-intake-dialog' in html
    url=f'/warehouse/intake/{order.id}'
    response=client.get(url+'?partial=1');assert response.status_code==200
    fragment=response.get_data(as_text=True);assert 'value="300"' in fragment and 'QUICK-500' in fragment and '<html' not in fragment
    assert WarehouseEvent.query.count()==count
    assert client.post(url,data={}).status_code==400
    fields={key:re.search(r'name="'+key+r'" value="([^"]+)"',fragment).group(1) for key in ('access_csrf','command_id','revision')}
    response=client.post(url+'?partial=1',data={**fields,**data,'quantity':'100','mode':'transfer'})
    assert response.status_code==200 and response.json['redirect'].endswith('view=incoming')
    standalone=client.get(url);assert standalone.status_code==200 and '<html' in standalone.get_data(as_text=True)
print('PASS: combined transfer/receipt, partial quantity, quarantine only, exact-once replay, no half booking on failed receipt, over-delivery and permissions blocked, row/dialog/form GET without writes, live remaining quantity, CSRF, transfer-only and no-JS page.')
