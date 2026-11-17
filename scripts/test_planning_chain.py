"""Expired availability and inherited queue times, using isolated synthetic data."""
import runpy
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

fixture=runpy.run_path(str(Path(__file__).with_name('test_order_planning.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking,QuantityReport,MachineControlCommand,MachinePlanningSettings,ProductionPlanEntry,MachineToolState
from factoryos.modules.production.services import planning_service as planning
from factoryos.modules.production.routes.planning_routes import fold_choice
from factoryos.core.models.change_log import ChangeLog

with app.app_context():
    admin=User.query.filter_by(username='test').one()
    machine=Machine(machine_no='CHAIN-MACHINE',machine_status='aktiv')
    tool=Tool(tool_no='CHAIN-TOOL',name='Kettenprüfung',cavities=2)
    slow=Order(order_no='CHAIN-RUNNING',tool_no=tool.tool_no,target_qty=120,cycle_time_s=60,status='open')
    first=Order(order_no='CHAIN-FIRST',tool_no=tool.tool_no,target_qty=120,cycle_time_s=60,status='open')
    second=Order(order_no='CHAIN-SECOND',tool_no=tool.tool_no,target_qty=240,cycle_time_s=60,status='open')
    db.session.add_all([machine,tool,slow,first,second]);db.session.commit()
    # Internal storage is UTC: 15:00 UTC = 16:00 CET; 20:00 UTC = 21:00 CET.
    now=datetime(2026,11,17,19,9)
    expired=datetime(2026,11,17,15)
    future=datetime(2026,11,17,20)
    settings=SimpleNamespace(week_start_day=0,week_start_time='00:00',week_end_day=6,week_end_time='23:59')
    active=TimeBooking(user_id=admin.id,machine_id=machine.id,order_id=slow.id,
        process='PROD',type='START',start_time=now-timedelta(hours=8))
    availability=MachinePlanningSettings(machine_id=machine.id,available_from=expired,availability_note='Frühere Schätzung wegen Abweichung')
    db.session.add_all([active,availability]);db.session.commit()

    def change(action,entry=None,**kwargs):
        return planning.modify_plan(admin.id,planning.planning_version(),action,machine.id,
            entry_id=entry.id if entry else None,now=now,**kwargs)
    change('add',order_id=first.id,setup_minutes=30)
    change('add',order_id=second.id,setup_minutes=15)
    first_entry,second_entry=planning.queue(machine.id)
    # Saved values from the old form must not silently postpone the new chain.
    first_entry.not_before=future+timedelta(days=4)
    second_entry.not_before=future+timedelta(days=8)
    db.session.commit()

    def lane(at=now,exceptions=None):
        return next(item for item in planning.build_schedule(at,settings,exceptions or [])['machines'] if item['machine'].id==machine.id)
    def counts():
        return tuple(model.query.count() for model in (TimeBooking,QuantityReport,MachineControlCommand,MachineToolState,ChangeLog))
    before=counts();version=planning.planning_version()
    current=lane()
    assert current['availability_expired'] and current['availability_needs_update']
    assert '17.11.2026 16:00:00 CET' in current['error'] and 'erneut rot' in current['error']
    assert 'CHAIN-RUNNING läuft weiterhin' in current['error']
    assert all(row['start'] is None for row in current['rows'])
    assert counts()==before and planning.planning_version()==version

    change('availability',available_from=future,availability_note='Neues erwartetes Ende wegen Abweichung')
    current=lane();a,b=current['rows']
    assert not current['error'] and not current['availability_needs_update']
    assert a['inherited_ready_at']==future and a['setup_start']==future
    assert a['start']==future+timedelta(minutes=30)
    assert a['end']==future+timedelta(minutes=90)
    assert b['setup_start']==a['end'] and b['start']==a['end']+timedelta(minutes=15)
    assert b['end']==b['start']+timedelta(hours=2)
    assert a['start_source']=='Verfügbarkeitsschätzung der Maschine'
    assert b['start_source']=='Ende von Auftrag CHAIN-FIRST'
    assert current['queue_ready_at']==b['end']
    assert first_entry.not_before==future+timedelta(days=4)  # read does not migrate stored data
    assert lane(future)['availability_needs_update']  # reached but still not completed
    again=lane(future+timedelta(hours=1))
    assert '17.11.2026 21:00:00 CET' in again['error']

    # Setup and production continue to obey shutdowns, not just wall-clock addition.
    closed=SimpleNamespace(start_at=future,end_at=future+timedelta(hours=1),title='Arbeitsfreie Stunde')
    shifted=lane(exceptions=[closed])['rows']
    assert shifted[0]['setup_start']==future+timedelta(hours=1)
    assert shifted[0]['start']==future+timedelta(minutes=90)
    assert shifted[1]['setup_start']==shifted[0]['end']

    # Invalid new estimates and legacy independent starts roll back completely.
    for bad in (expired,now):
        before=counts();version=planning.planning_version()
        try:change('availability',available_from=bad,availability_note='Erneute Schätzung')
        except ValueError as error:
            assert 'Zukunft' in str(error);db.session.rollback()
        else:raise AssertionError('Past/equal availability accepted')
        assert planning.planning_version()==version and counts()==before
    try:change('update',entry=first_entry,setup_minutes=10,not_before=future)
    except ValueError as error:
        assert 'Planbeginn' in str(error);db.session.rollback()
    else:raise AssertionError('Independent start accepted')

    # Editing setup alone clears its obsolete constraint and recalculates successors.
    change('update',entry=first_entry,setup_minutes=60)
    assert first_entry.not_before is None
    rows=lane()['rows']
    assert rows[0]['start']==future+timedelta(hours=1)
    assert rows[1]['setup_start']==rows[0]['end']
    change('reorder',ordered_ids=[second_entry.id,first_entry.id])
    reordered=lane()['rows']
    assert reordered[0]['entry'].order_id==second.id and reordered[0]['setup_start']==future
    assert reordered[1]['setup_start']==reordered[0]['end']
    change('reorder',ordered_ids=[first_entry.id,second_entry.id])

    # Ordinary winter time uses Automatic, not a misleading Summer-time selection.
    assert fold_choice(future)==''
    assert fold_choice(datetime(2026,10,25,0,30))=='0'
    assert fold_choice(datetime(2026,10,25,1,30))=='1'

    class FixedClock(datetime):
        @classmethod
        def utcnow(cls):return now
    client=app.test_client()
    with client.session_transaction() as session:
        session['_user_id']=str(admin.id);session['_fresh']=True;session['access_csrf']='chain-test'
    with patch.object(planning,'datetime',FixedClock):
        html=client.get('/production/planning').get_data(as_text=True)
        assert 'name="not_before"' not in html and 'Frühester Planbeginn' not in html
        section=html.split(f'id="plan-machine-{machine.id}"',1)[1].split('</section>',1)[0]
        assert 'Automatisch übernommener Rüstbeginn' in section and '21:00:00 CET' in section
        assert 'Erste Stunde (Sommerzeit)</option>' in section  # available only for ambiguous input
        assert 'value="0" selected' not in section
        response=client.post('/production/planning',data=dict(access_csrf='chain-test',version=planning.planning_version(),
            action='update',machine_id=machine.id,entry_id=first_entry.id,setup_minutes='20',not_before='2026-11-17T16:00:00'))
        assert response.status_code==400 and 'Planbeginn wird aus der Maschinenverfügbarkeit' in response.get_data(as_text=True)
    availability.available_from=expired;db.session.commit()
    with patch.object(planning,'datetime',FixedClock):
        html=client.get('/production/planning').get_data(as_text=True)
        section=html.split(f'id="plan-machine-{machine.id}"',1)[1].split('</section>',1)[0]
        assert '16:00:00 CET' in section and 'erneut rot' in section
        assert 'class="planning-settings" open' in section

    # An old assumption does not block an idle machine or a fresh, usable ETA.
    active.end_time=now;db.session.commit()
    assert not lane()['error'] and not lane()['availability_needs_update']
    active.end_time=None;active.start_time=now-timedelta(minutes=5);db.session.commit()
    trusted=lane()
    assert not trusted['error'] and not trusted['availability_needs_update']
    assert trusted['rows'][0]['start_source']=='Endprognose von Auftrag CHAIN-RUNNING'
    availability.available_from=future;db.session.commit()
    reliable_eta=planning.order_statistics(slow,now,settings,[])['eta']
    assert reliable_eta>future
    assert lane()['rows'][0]['setup_start']==reliable_eta
    # Inactive machines and corrupt multiple bookings are never unlocked by a guess.
    machine.machine_status='inaktiv';availability.available_from=future;db.session.commit()
    assert lane()['rows'][0]['start'] is None and 'nicht aktiv' in lane()['error']
    machine.machine_status='aktiv'
    extra=TimeBooking(user_id=admin.id,machine_id=machine.id,process='FREI',type='START',start_time=now-timedelta(minutes=2))
    db.session.add(extra);db.session.commit()
    assert 'Mehrere aktive' in lane()['error'] and lane()['rows'][0]['start'] is None
    print('PASS: explicit 16:00/21:00 expiry reason, read-only inherited setup/production/predecessor chain, obsolete constraints ignored, calendar delays, reordered successors, future validation/rollback, legacy form rejection, automatic winter/DST choice, idle/trusted ETA and inactive/multiple-booking guards')
