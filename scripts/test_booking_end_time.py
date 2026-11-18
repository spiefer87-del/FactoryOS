"""End correction: preview, atomic FREE adjustment, audit, ACL and final quantities."""
import re
import runpy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

fixture = runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app = fixture['app']
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog
from factoryos.core.services.activity_presenter import present_change_logs
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking, QuantityReport, OrderCompletion
from factoryos.modules.production.services.booking_time_service import (
    end_correction_plan, apply_end_correction, revision, parse_local_start, BookingOverlapError)
from factoryos.modules.production.services.order_statistics import order_statistics
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from scripts.upgrade_order_statistics import run_upgrade

with app.app_context():
    run_upgrade()
    user = db.session.merge(fixture['user'])
    machine = Machine(machine_no='END-CORRECTION', machine_status='aktiv')
    order = Order(order_no='END-CORRECTION', status='finished', target_qty=100, cycle_time_s=60)
    db.session.add_all([machine, order]); db.session.flush()
    start = datetime(2026, 11, 2, 8)
    old_end = start+timedelta(hours=4)
    booking = TimeBooking(user_id=user.id, machine_id=machine.id, order_id=order.id,
                          process='PROD', type='START', start_time=start, end_time=old_end)
    free = TimeBooking(user_id=user.id, machine_id=machine.id, process='FREI', type='START',
                       start_time=old_end)
    completion = OrderCompletion(order_id=order.id,user_id=user.id,machine_id=machine.id,
        good_qty=100,scrap_qty=3,reported_good_qty=20,reported_scrap_qty=1,target_qty=100,
        previous_status='running',reason='Sollstückzahl erreicht',source='machine',
        command_id=str(uuid4()),payload_hash='test',closed_at=old_end)
    report = QuantityReport(user_id=user.id,machine_id=machine.id,order_id=order.id,
                            good_qty=20,scrap_qty=1,created_at=start+timedelta(hours=1))
    db.session.add_all([booking,free,completion,report]);db.session.commit()
    def client_for(person):
        client=app.test_client()
        with client.session_transaction() as session:
            session['_user_id']=str(person.id);session['_fresh']=True
        return client
    client=client_for(user)
    path=f'/production/booking/{booking.id}/end-time'
    assert app.test_client().get(path).status_code==302
    reader=User(username='end-reader',password_hash='unused',active=True,
                role=Role(name='end-reader',active=True,permissions=[Permission(name='production.view')]))
    db.session.add(reader);db.session.commit();restricted=client_for(reader)
    assert restricted.get(path).status_code==403 and restricted.post(path,data={}).status_code==403
    reader.role.permissions.append(Permission.query.filter_by(name='production.edit_booking_time').one())
    db.session.commit()
    assert restricted.get(path).status_code==200  # Explicit grant, no admin-only shortcut.
    page=client.get(path);assert page.status_code==200
    html=page.get_data(as_text=True)
    assert 'Endzeit korrigieren' in html and 'name="end_time"' in html
    assert 'name="start_time"' not in html
    assert 'Endzeit korrigieren' in client.get(f'/production/booking/{booking.id}/start-time').get_data(as_text=True)
    assert 'Endzeitkorrektur öffnen' in client.get(f'/production/booking/{booking.id}/review').get_data(as_text=True)
    def hidden(name):return re.search(r'name="'+name+r'" value="([^"]*)"',html)[1]
    payload=dict(access_csrf=hidden('access_csrf'),revision=hidden('revision'),
        end_time='2026-11-02T11:00:00',fold='',reason='Produktion war bereits zwei Stunden vorher fertig')
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={**payload,'intent':'commit'}).status_code==400
    assert client.post(path,data={**payload,'intent':'preview','reason':'kurz'}).status_code==400
    before_count=TimeBooking.query.count();before_logs=ChangeLog.query.count()
    preview=client.post(path,data={**payload,'intent':'preview'})
    assert preview.status_code==200 and 'Frei-Buchung' in preview.get_data(as_text=True)
    assert booking.end_time==old_end and free.start_time==old_end
    assert ChangeLog.query.count()==before_logs
    # Changing even one second after preview requires a new preview.
    assert client.post(path,data={**payload,'end_time':'2026-11-02T11:00:01','intent':'commit'}).status_code==400
    saved=client.post(path,data={**payload,'intent':'commit'})
    assert saved.status_code==302
    db.session.refresh(booking);db.session.refresh(free);db.session.refresh(completion)
    new_end=start+timedelta(hours=2)
    assert booking.start_time==start and booking.end_time==new_end and free.start_time==new_end
    assert free.end_time is None and TimeBooking.query.count()==before_count
    assert completion.closed_at==old_end and completion.good_qty==100 and completion.scrap_qty==3
    assert order.status=='finished' and QuantityReport.query.count()>=1
    calendar=SimpleNamespace(week_start_day=0,week_start_time='04:30',week_end_day=5,week_end_time='06:00')
    stats=order_statistics(order,old_end+timedelta(hours=1),calendar,[])
    assert stats['working_seconds']==7200 and stats['last_end']==new_end
    assert stats['good']==100 and stats['scrap']==3
    timeline=get_machine_timeline('custom',now=old_end+timedelta(hours=1),
        range_start=start,range_end=old_end+timedelta(hours=2))
    lane=next(row for row in timeline['lanes'] if row['machine'].id==machine.id)
    actual=[item for item in lane['items'] if item.get('booking') and item['booking'].id==booking.id]
    assert len(actual)==1 and actual[0]['kind']=='actual' and abs(actual[0]['width']-100/3)<1e-8
    logs=ChangeLog.query.filter_by(entity_type='order',entity_id=order.id).all()
    event=next(row for row in logs if 'booking_end_correction' in row.changes)
    entry=event.changes['booking_end_correction']
    assert event.user_id==user.id and entry['end_time_utc']['old']==old_end.isoformat()
    assert entry['free_intervals'][0]['booking_id']==free.id
    view=present_change_logs([event])[0]
    assert view.action_label=='Produktions-Endzeit korrigiert'
    assert any(line['changed'] and line['old']=='02.11.2026 13:00:00 CET' and line['value']=='02.11.2026 11:00:00 CET' for line in view.lines)
    html=client.get(f'/orders/{order.id}').get_data(as_text=True)
    assert 'Endzeit der letzten Produktionsbuchung korrigieren' in html
    assert 'Endzeit korrigiert' in html and 'booking_end_correction' not in html
    assert 'Abschluss erfasst am' in html
    feed=client.get('/activity/?limit=all').get_data(as_text=True)
    assert 'Produktions-Endzeit korrigiert' in feed and 'booking_end_correction' not in feed

    # Later end shortens the same open FREE record, without changing its activity.
    apply_end_correction(booking,start+timedelta(hours=3),'Ende nach Schichtzettel berichtigt',revision(booking))
    assert free.start_time==booking.end_time==start+timedelta(hours=3)
    # A terminated FREE record can shrink to zero, but a real successor cannot move.
    free.end_time=old_end;db.session.commit()
    apply_end_correction(booking,old_end,'Ende anhand Protokoll bestätigt',revision(booking))
    assert free.start_time==free.end_time==old_end
    successor=TimeBooking(user_id=user.id,machine_id=machine.id,process='RUEST',type='START',
                          start_time=old_end,end_time=old_end+timedelta(hours=1))
    db.session.add(successor);db.session.commit()
    def rejected(stamp):
        try:end_correction_plan(booking,stamp,'Geprüfte Zeitkorrektur',now=old_end+timedelta(days=1))
        except ValueError:return
        raise AssertionError('Invalid correction accepted')
    for stamp in (start,start-timedelta(seconds=1),old_end,old_end+timedelta(days=2),old_end+timedelta(minutes=30)):
        rejected(stamp)
    assert successor.start_time==old_end
    # Same order on another machine also blocks overlapping production.
    other_machine=Machine(machine_no='END-CORRECTION-OTHER',machine_status='aktiv')
    db.session.add(other_machine);db.session.flush()
    parallel=TimeBooking(user_id=user.id,machine_id=other_machine.id,order_id=order.id,
        process='PROD',type='START',start_time=start+timedelta(hours=1),end_time=old_end)
    db.session.add(parallel);db.session.commit()
    rejected(start+timedelta(hours=2));db.session.delete(parallel);db.session.commit()
    # Legacy gap: no synthetic FREE activity is created and successor is unchanged.
    count=TimeBooking.query.count()
    apply_end_correction(booking,start+timedelta(hours=2),'Früheres Ende laut Schichtbericht',revision(booking))
    assert TimeBooking.query.count()==count and successor.start_time==old_end
    # Mutation of a dependent record after preview cannot be committed.
    old_revision=revision(booking)
    successor.end_time+=timedelta(minutes=1);db.session.commit()
    try:apply_end_correction(booking,start+timedelta(hours=3),'Nach Vorschau eingereichte Korrektur',old_revision)
    except ValueError:db.session.rollback()
    else:raise AssertionError('Stale revision accepted')
    assert booking.end_time==start+timedelta(hours=2)
    # No end may be supplied through correction to stop a running machine.
    booking.end_time=None;db.session.commit()
    assert client.get(path).status_code==400
    rejected(old_end)
    booking.end_time=old_end;db.session.commit()
    completed=Order.query.filter(Order.sampling.has(state='completed')).first()
    protected=TimeBooking(user_id=user.id,machine_id=other_machine.id,order_id=completed.id,
        process='MUSTER',type='START',start_time=start,end_time=old_end)
    db.session.add(protected);db.session.commit()
    assert client.get(f'/production/booking/{protected.id}/end-time').status_code==400
    # Seconds must remain visible in audit display, even within the same minute.
    audit=SimpleNamespace(id=999,entity_type='order',entity_id=order.id,entity_name=order.order_no,
        action='update',category='production',user=user,created_at=old_end,
        changes={'booking_end_correction':{'end_time_utc':{'old':'2026-11-02T12:00:01','new':'2026-11-02T12:00:02'}}})
    assert any(line['changed'] for line in present_change_logs([audit])[0].lines)
    assert parse_local_start('2026-10-25T02:30:00','1')-parse_local_start('2026-10-25T02:30:00','0')==timedelta(hours=1)
    for stamp in ('2026-03-29T02:30:00','2026-10-25T02:30:00'):
        try:parse_local_start(stamp)
        except ValueError:pass
        else:raise AssertionError('Invalid/ambiguous DST input accepted')

print('PASS: earlier/later end, open/ended/zero FREE adjustments, completed orders and preserved final quantities/confirmation time, corrected net/runtime/end statistics, readable second-precision audit/feed, preview binding, CSRF and ACL, unchanged successor and same-order overlap guards, legacy gaps, stale revisions, active booking/completed sampling protection and DST')
