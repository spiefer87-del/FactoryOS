"""Calendar-aware runtime boundary, overrun display and unchanged source data."""
import runpy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
fixture = runpy.run_path(str(ROOT / 'scripts/test_sampling_orders.py'))
app = fixture['app']
from flask import render_template
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking, QuantityReport, ProductionCalendarSettings
from factoryos.modules.production.services.order_statistics import (
    order_statistics, nominal_limit_at, duration, local_label, runtime_difference)
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from factoryos.modules.production_deviations.models import ProductionDeviationConfirmation
from factoryos.core.models.change_log import ChangeLog

calendar = SimpleNamespace(week_start_day=0, week_start_time='04:30',
                           week_end_day=5, week_end_time='06:00')
# The budget crosses a weekly closure, a holiday and a gap between bookings.
friday = datetime(2026, 11, 6, 23)
saturday = datetime(2026, 11, 7, 5)
monday = datetime(2026, 11, 9, 5)
holiday = SimpleNamespace(start_at=monday, end_at=monday+timedelta(hours=1), title='Test')
intervals = [(friday, saturday), (monday, monday+timedelta(hours=4))]
assert nominal_limit_at(intervals, 8*3600, calendar, [holiday]) == monday+timedelta(hours=3)
assert nominal_limit_at(intervals, 6*3600, calendar, [holiday]) == saturday
assert nominal_limit_at(intervals, 10*3600, calendar, [holiday]) is None
assert nominal_limit_at([(friday, monday+timedelta(hours=4))], 8*3600, calendar, [holiday]) == monday+timedelta(hours=1, minutes=30)
assert nominal_limit_at(intervals+intervals, 8*3600, calendar, [holiday]) == monday+timedelta(hours=3)
assert nominal_limit_at(intervals, None, calendar, []) is None
# Screenshot arithmetic: 43h20m nominal vs 53h48m working, not 100h18m gross.
sample = dict(planned_seconds=156000, working_seconds=193680, gross_seconds=361080,
              forecast=dict(cavities_assumed=False), deviation=dict(kind='overdue'))
assert runtime_difference(sample)['seconds'] == 37680
assert duration(runtime_difference(sample)['seconds']) == '10 Std 28 Min'

with app.app_context():
    user = db.session.merge(fixture['user'])
    machine = Machine(machine_no='OVERRUN-MACHINE', machine_status='aktiv')
    tool = Tool(tool_no='OVERRUN-TOOL', name='Overrun', cavities=1)
    order = Order(order_no='OVERRUN-ORDER', tool_no=tool.tool_no,
                  target_qty=60, cycle_time_s=60, status='running')
    db.session.add_all([machine, tool, order]); db.session.flush()
    now = datetime(2026, 11, 17, 12)
    booking = TimeBooking(user_id=user.id, machine_id=machine.id, order_id=order.id,
                          tool_no=tool.tool_no, type='START', process='PROD',
                          start_time=now-timedelta(hours=2))
    db.session.add(booking)
    if not ProductionCalendarSettings.query.first():
        db.session.add(ProductionCalendarSettings(**vars(calendar)))
    db.session.commit()
    def counts():
        return tuple(model.query.count() for model in
                     (TimeBooking, QuantityReport, ChangeLog, ProductionDeviationConfirmation))
    before = counts()
    stats = order_statistics(order, now, calendar, [])
    assert stats['runtime_difference']['seconds'] == 3600
    assert stats['nominal_limit_at'] == now-timedelta(hours=1)
    assert stats['good'] == 0 and stats['eta'] is None
    signature = stats['deviation']['signature']
    reason = ProductionDeviationConfirmation(order_id=order.id, signature=signature,
        kind='overdue', category='Sonstiger Grund', reason='Testlauf mit bewusst langsamerem Zyklus',
        user_id=user.id, snapshot=stats['deviation']['snapshot'])
    db.session.add(reason); db.session.commit()
    before = counts()
    stats = order_statistics(order, now, calendar, [])
    assert stats['deviation']['confirmation'] and stats['runtime_difference']['seconds'] == 3600

    def lane(start, end):
        timeline = get_machine_timeline('custom', now, start, end)
        return next(row for row in timeline['lanes'] if row['machine'].id == machine.id)
    row = lane(now-timedelta(hours=3), now+timedelta(hours=1))
    actual = [item for item in row['items'] if item['kind'] == 'actual']
    assert [item['runtime_phase'] for item in actual] == ['nominal', 'overrun']
    assert [item['width'] for item in actual] == [25, 25]
    assert actual[0]['left']+actual[0]['width'] == actual[1]['left']
    assert row['active_runtime']['position'] == 50
    assert row['active_runtime']['duration_label'] == '1 Std 0 Min'
    narrow = lane(now-timedelta(minutes=30), now+timedelta(minutes=30))
    assert narrow['active_runtime']['position'] is None and narrow['active_runtime']['before_range']
    assert [item['runtime_phase'] for item in narrow['items']] == ['overrun']
    past = lane(now-timedelta(hours=2), now-timedelta(minutes=90))
    assert past['active_runtime']['after_range'] and all(i['runtime_phase']=='nominal' for i in past['items'])
    future = lane(now+timedelta(hours=1), now+timedelta(hours=2))
    assert future['items'] == []
    for data in (row, narrow, past, future):
        for item in data['items']:
            assert 0 <= item['left'] < 100 and 0 < item['width'] <= 100-item['left']
    assert counts() == before

    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id']=str(user.id); session['_fresh']=True
    # HTTP rendering with fixed clock: no dependence on the day this test runs.
    with patch('factoryos.modules.orders.routes.detail_routes.order_statistics', return_value=stats):
        response = client.get(f'/orders/{order.id}')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    metrics = ['nominal','difference','working','remaining','gross']
    assert [html.index(f'data-runtime="{key}"') for key in metrics] == sorted(html.index(f'data-runtime="{key}"') for key in metrics)
    assert '+1 Std 0 Min' in html
    with patch('factoryos.modules.production.routes.dashboard_routes.get_machine_timeline',
               side_effect=lambda *args, **kwargs: get_machine_timeline('24h', now)):
        response = client.get('/production/booking')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'timeline-nominal-line' in html and '+1 Std 0 Min über Soll' in html
    assert 'runtime-nominal' in html and 'runtime-overrun' in html

    booking.start_time=now-timedelta(minutes=30);db.session.commit()
    under = order_statistics(order, now, calendar, [])
    assert under['runtime_difference'] is None and under['nominal_limit_at'] is None
    with app.test_request_context('/'):
        html = render_template('orders/statistics.html',statistics=under,
            can_correct_time=False,duration=duration,local_label=local_label)
    assert 'data-runtime="difference"' not in html
    booking.start_time=now-timedelta(hours=1);db.session.commit()
    exact = order_statistics(order, now, calendar, [])
    assert exact['runtime_difference'] is None and exact['nominal_limit_at'] == now
    booking.start_time=now-timedelta(hours=2);tool.cavities=None;db.session.commit()
    assert order_statistics(order, now, calendar, [])['runtime_difference']['provisional']
    tool.cavities=1;booking.end_time=now;booking.start_time=now-timedelta(minutes=30)
    order.status='finished'
    db.session.add(QuantityReport(user_id=user.id,machine_id=machine.id,order_id=order.id,
                                 good_qty=60,scrap_qty=0,created_at=now));db.session.commit()
    fast = order_statistics(order, now, calendar, [])
    assert fast['runtime_difference']['over'] is False and fast['runtime_difference']['seconds']==1800
    order.cycle_time_s=None;db.session.commit()
    missing = order_statistics(order, now, calendar, [])
    assert missing['runtime_difference'] is None and missing['nominal_limit_at'] is None

print('PASS: calendar-aware nominal boundary, gaps/holidays/overlaps, screenshot arithmetic, exact/under/over budget, confirmed overtime visible, completed underrun, provisional/missing values, split/clipped timeline and offscreen markers, HTTP rendering and KPI order, no fabricated quantities or read-time writes')
