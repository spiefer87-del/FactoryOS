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
from factoryos.modules.production.models import TimeBooking,SetupOperation,MachineToolState
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.order_statistics import local_time
from factoryos.modules.booking_review.service import revision
from scripts.upgrade_booking_review import run_upgrade

with app.app_context():
    run_upgrade();run_upgrade()
    user=db.session.merge(fixture['user']);tool=db.session.merge(fixture['tool'])
    machine=Machine(machine_no='SETUP-REVIEW',machine_status='aktiv');db.session.add(machine);db.session.flush()
    now=datetime.utcnow().replace(microsecond=0)
    state=MachineToolState(machine_id=machine.id,status='mounted',tool_no=tool.tool_no,updated_by_id=user.id,updated_at=now)
    row=TimeBooking(user_id=user.id,machine_id=machine.id,tool_no=tool.tool_no,type='START',process='RUEST',start_time=now-timedelta(days=3),end_time=now-timedelta(days=3,hours=-1))
    db.session.add_all([state,row]);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
    path=f'/production/booking/{row.id}/review';assert client.get(path).status_code==200
    with client.session_transaction() as s:csrf=s['access_csrf']
    def values(action):return dict(action=action,access_csrf=csrf,reason='Korrektur der Testphase',revision=revision(row),start=local_time(now-timedelta(days=4)).strftime('%Y-%m-%dT%H:%M:%S'),end=local_time(now-timedelta(days=4,hours=-1)).strftime('%Y-%m-%dT%H:%M:%S'))
    data=values('move')
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit'}).status_code==303
    assert row.start_time==now-timedelta(days=4)
    op=SetupOperation(machine_id=machine.id,tool_no=tool.tool_no,kind='RUEST',outcome='completed',started_at=row.start_time,ended_at=row.end_time,started_by_id=user.id,start_booking_id=row.id)
    db.session.add(op);db.session.commit()
    data=values('move');data['start']=local_time(now-timedelta(days=5)).strftime('%Y-%m-%dT%H:%M:%S');data['end']=local_time(now-timedelta(days=5,hours=-1)).strftime('%Y-%m-%dT%H:%M:%S')
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    op.note='Parallel geändert';db.session.commit()
    assert client.post(path,data={**data,'intent':'commit'}).status_code==409
    data['revision']=revision(row)
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit'}).status_code==303
    assert op.started_at==row.start_time and op.ended_at==row.end_time
    assert client.post(path,data={**values('cancel'),'intent':'preview'}).status_code==400
    reader=User(username='setup-time-only',password_hash='unused',active=True,role=Role(name='setup-time-only',active=True,permissions=[Permission.query.filter_by(name='production.edit_setup_time').one(),Permission(name='production.view')]))
    db.session.add(reader);db.session.commit();denied=app.test_client()
    with denied.session_transaction() as s:s['_user_id']=str(reader.id);s['_fresh']=True;s['access_csrf']='reader'
    assert denied.post(path,data={**values('delete'),'access_csrf':'reader','intent':'preview'}).status_code==403
    data=values('delete');before=ChangeLog.query.filter_by(category='booking_review').count()
    assert client.post(path,data={**data,'intent':'commit','confirm_delete':'yes'}).status_code==400
    assert client.post(path,data={**data,'intent':'preview'}).status_code==200
    assert client.post(path,data={**data,'intent':'commit'}).status_code==400
    row_id=row.id;op_id=op.id
    assert client.post(path,data={**data,'intent':'commit','confirm_delete':'yes'}).status_code==303
    assert db.session.get(TimeBooking,row_id) is None and db.session.get(SetupOperation,op_id) is None
    assert client.get(path).status_code==404
    assert state.status=='mounted' and state.tool_no==tool.tool_no and state.updated_at==now
    assert ChangeLog.query.filter_by(category='booking_review').count()==before+1
    audit=ChangeLog.query.filter_by(category='booking_review').order_by(ChangeLog.id.desc()).first()
    assert audit.changes['booking_review']['old']['id']==row_id and audit.changes['booking_review']['setup_old']['id']==op_id and audit.action=='delete'
    from sqlalchemy import text
    extra=TimeBooking(user_id=user.id,machine_id=machine.id,type='START',process='FREI',start_time=now-timedelta(days=7),end_time=now-timedelta(days=6))
    db.session.add(extra);db.session.commit()
    db.session.execute(text('CREATE TABLE review_external_link (id INTEGER PRIMARY KEY, booking_id INTEGER REFERENCES time_bookings(id))'))
    db.session.execute(text('INSERT INTO review_external_link (booking_id) VALUES (:id)'),{'id':extra.id});db.session.commit()
    extra_path=f'/production/booking/{extra.id}/review'
    extra_data=dict(action='delete',access_csrf=csrf,reason='Darf mit Bezug nicht gelöscht werden',revision=revision(extra),intent='preview')
    response=client.post(extra_path,data=extra_data)
    assert response.status_code==400 and 'review_external_link' in response.get_data(as_text=True)
    db.session.execute(text('DROP TABLE review_external_link'));db.session.commit()
    extra_data['revision']=revision(extra)
    assert client.post(extra_path,data=extra_data).status_code==200
    extra_id=extra.id
    assert client.post(extra_path,data={**extra_data,'intent':'commit','confirm_delete':'yes'}).status_code==303
    assert db.session.get(TimeBooking,extra_id) is None
print('PASS: legacy setup correction, paired setup sync, setup revision conflict, no partial cancellation, dedicated delete permission, preview and explicit confirmation, physical deletion and audit, mounted tool unchanged')
