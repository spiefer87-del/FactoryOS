import runpy,re
from pathlib import Path
from datetime import datetime,timedelta
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,QuantityReport
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.booking_review.service import revision
from factoryos.modules.production.services.booking_time_service import revision as start_revision
from factoryos.modules.production.services.order_statistics import local_time
from scripts.upgrade_booking_review import run_upgrade

with app.app_context():
    run_upgrade();run_upgrade()
    user=db.session.merge(fixture['user']);machine=Machine(machine_no='REVIEW-TEST',machine_status='aktiv')
    order=Order(order_no='REVIEW-TEST',status='in_arbeit')
    db.session.add_all([machine,order]);db.session.flush()
    now=datetime.utcnow().replace(microsecond=0)
    row=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=order.id,process='PROD',type='START',start_time=now-timedelta(days=3),end_time=now-timedelta(days=3,hours=-1))
    db.session.add(row);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
    path=f'/production/booking/{row.id}/review'
    assert client.get(path).status_code==200
    with client.session_transaction() as s:csrf=s['access_csrf']
    data=dict(access_csrf=csrf,action='move',start=local_time(now-timedelta(days=4)).strftime('%Y-%m-%dT%H:%M:%S'),end=local_time(now-timedelta(days=4,hours=-1)).strftime('%Y-%m-%dT%H:%M:%S'),reason='Testbuchung falsch erfasst',revision=revision(row))
    assert client.post(path,data={**data,'intent':'commit'}).status_code==400
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit'}).status_code==303
    assert row.start_time==now-timedelta(days=4)
    assert client.post(path,data={**data,'intent':'preview'}).status_code==409
    role=Role(name='review-readonly',permissions=[Permission(name='production.view')],active=True)
    reader=User(username='review-readonly',password_hash='unused',role=role,active=True);db.session.add(reader);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as s:s['_user_id']=str(reader.id);s['_fresh']=True
    assert denied.get(path).status_code==200
    with denied.session_transaction() as s:s['access_csrf']='reader-test';reader_csrf=s['access_csrf']
    cancel=dict(access_csrf=csrf,action='cancel',reason='Testbuchung versehentlich angelegt',revision=revision(row))
    assert denied.post(path,data={**cancel,'access_csrf':reader_csrf,'intent':'preview'}).status_code==403
    assert client.post(path,data={**cancel,'access_csrf':'wrong','intent':'preview'}).status_code==400
    assert client.post(path,data={**cancel,'intent':'preview'}).status_code==200
    assert client.post(path,data={**cancel,'intent':'commit'}).status_code==303
    assert row.type=='STORNO' and row.start_time==row.end_time
    assert ChangeLog.query.filter_by(category='booking_review').count()==2
    assert client.post(path,data={**cancel,'revision':revision(row),'intent':'preview'}).status_code==400
    blocker=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=order.id,process='PROD',type='START',start_time=now-timedelta(hours=5),end_time=now-timedelta(hours=3))
    active=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=order.id,process='PROD',type='START',start_time=now-timedelta(hours=2))
    db.session.add_all([blocker,active]);db.session.commit()
    start_path=f'/production/booking/{active.id}/start-time'
    assert client.get(start_path).status_code==200
    response=client.post(start_path,data=dict(access_csrf=csrf,revision=start_revision(active),start_time=local_time(now-timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S'),reason='Korrektur Testphase',intent='preview'))
    assert response.status_code==400
    assert f'/production/booking/{blocker.id}/review' in response.get_data(as_text=True)
    protected=dict(access_csrf=csrf,action='cancel',reason='Nicht erlaubt Test',revision=revision(active),intent='preview')
    assert client.post(f'/production/booking/{active.id}/review',data=protected).status_code==400
    db.session.add(QuantityReport(user_id=user.id,order_id=order.id,machine_id=machine.id,good_qty=1,scrap_qty=0));db.session.commit()
    assert client.post(f'/production/booking/{blocker.id}/review',data={**protected,'revision':revision(blocker)}).status_code==400
    from factoryos.modules.production.models import SetupOperation
    linked=TimeBooking(user_id=user.id,machine_id=machine.id,process='FREI',type='START',start_time=now-timedelta(days=6),end_time=now-timedelta(days=5))
    db.session.add(linked);db.session.flush()
    operation=SetupOperation(machine_id=machine.id,tool_no=fixture['tool'].tool_no,kind='RUEST',outcome='completed',started_at=linked.start_time,ended_at=linked.end_time,started_by_id=user.id,start_booking_id=linked.id)
    db.session.add(operation);db.session.commit()
    assert client.post(f'/production/booking/{linked.id}/review',data={**protected,'revision':revision(linked)}).status_code==400
print('PASS: overlap link, review, readonly ACL, CSRF, preview required, move, stale revision, audited zero-time cancellation, active and reported-quantity protection; upgrade twice')
