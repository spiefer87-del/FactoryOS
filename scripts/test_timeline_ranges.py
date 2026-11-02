"""Window selection is read-only and independent of live machine controls."""
import runpy
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_machine_control.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,QuantityReport,MachineControlCommand
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.timeline_service import get_machine_timeline,parse_timeline_range,HORIZONS,_axis_ticks

for args in [("",""),("2026-11-02T12:00","2026-11-02T12:00"),("2026-11-03T12:00","2026-11-02T12:00"),
             ("2026-01-01T00:00","2028-01-01T00:00"),("2026-03-29T02:15","2026-03-29T04:00"),
             ("2026-10-25T02:30","2026-10-25T04:00"),("9999-01-01T00:00","9999-01-02T00:00")]:
    try:parse_timeline_range(*args)
    except ValueError:pass
    else:raise AssertionError(f"Invalid range accepted: {args}")
start,end=parse_timeline_range("2026-11-02T13:00","2026-11-02T14:00")
assert start==datetime(2026,11,2,12) and end-start==timedelta(hours=1)
start,end=parse_timeline_range("2026-10-25T02:30","2026-10-25T02:30","0","1")
assert end-start==timedelta(hours=1)
ticks=_axis_ticks(start,end,timedelta(minutes=30))
assert any("CEST" in t["label"] for t in ticks) and any("CET" in t["label"] for t in ticks)
assert len(_axis_ticks(datetime(2026,11,2,12,7),datetime(2026,11,2,12,57),timedelta(minutes=10)))==5

with app.app_context():
    admin=User.query.filter_by(username="test").one()
    machine=Machine(machine_no="WINDOW-TEST",machine_status="aktiv")
    old=Order(order_no="WINDOW-OLD",article="A001",tool_no="W001",target_qty=1000,cycle_time_s=60)
    live=Order(order_no="WINDOW-LIVE",article="A001",tool_no="W001",target_qty=1000,cycle_time_s=60)
    db.session.add_all([machine,old,live]);db.session.flush()
    now=datetime(2026,11,2,12)
    historical=TimeBooking(user_id=admin.id,machine_id=machine.id,order_id=old.id,type="START",process="PROD",
        start_time=datetime(2026,10,1,8),end_time=datetime(2026,10,1,10))
    current=TimeBooking(user_id=admin.id,machine_id=machine.id,order_id=live.id,type="START",process="PROD",tool_no="W001",start_time=now-timedelta(hours=1))
    future_record=TimeBooking(user_id=admin.id,machine_id=machine.id,type="START",process="WARTUNG",
        start_time=now+timedelta(hours=2),end_time=now+timedelta(hours=3))
    db.session.add_all([historical,current,future_record]);db.session.commit()
    def counts():return tuple(model.query.count() for model in (TimeBooking,QuantityReport,MachineControlCommand,ChangeLog))
    before=counts()
    def lane(data):return next(item for item in data["lanes"] if item["machine"].id==machine.id)
    for key,hours in [("1h",1),("8h",8),("24h",24),("3d",72),("7d",168),("30d",720)]:
        data=get_machine_timeline(key,now)
        assert (data["range_end"]-data["range_start"]).total_seconds()==hours*3600
        assert data["show_now"] and 0<data["now_position"]<100
        assert lane(data)["active_booking"].id==current.id
        assert len(data["ticks"])<=40 and data["track_width"]>=840
    past=get_machine_timeline("custom",now,datetime(2026,10,1,8,30),datetime(2026,10,1,9,30))
    assert not past["show_now"]
    assert lane(past)["active_booking"].id==current.id  # not the historical order!
    items=lane(past)["items"]
    assert len(items)==1 and items[0]["booking"].id==historical.id and items[0]["left"]==0 and items[0]["width"]==100
    future=get_machine_timeline("custom",now,now+timedelta(hours=2),now+timedelta(hours=4))
    assert not future["show_now"]
    assert lane(future)["items"] and all(i["kind"]=="forecast" for i in lane(future)["items"])
    beyond=get_machine_timeline("custom",now,now+timedelta(days=60),now+timedelta(days=61))
    assert lane(beyond)["items"]==[]  # no ghost minimum-width forecast after ETA
    assert lane(beyond)["active_booking"].id==current.id
    assert counts()==before
    client=app.test_client()
    with client.session_transaction() as session:session["_user_id"]=str(admin.id);session["_fresh"]=True
    for key in HORIZONS:
        response=client.get("/production/booking",query_string={"zeitraum":key})
        assert response.status_code==200
        assert f'value="{key}" selected' in response.get_data(as_text=True)
    response=client.get("/production/booking",query_string={"zeitraum":"custom","von":"2000-01-01T00:00","bis":"2000-01-02T00:00"})
    html=response.get_data(as_text=True)
    assert response.status_code==200 and 'data-now-marker' not in html
    assert 'value="custom" selected' in html and 'id="machine-control-dialog"' in html
    assert "Live-Stand jetzt" in html and 'name="von"' in html and 'name="bis"' in html
    assert "Europe/Berlin" in html and "Auftragsreihenfolgen" in html
    response=client.get("/production/booking",query_string={"zeitraum":"custom","von":"2026-11-02T12:00","bis":"2026-11-01T12:00"})
    assert response.status_code==400 and "Eingabe korrigieren" in response.get_data(as_text=True)
    assert 'value="2026-11-02T12:00"' in response.get_data(as_text=True)
    assert client.get("/production/booking?zeitraum=custom").status_code==400
    assert client.get("/production/booking?zeitraum=invalid").status_code==200
    assert app.test_client().get("/production/booking?zeitraum=30d").status_code==302
    assert counts()==before
print("PASS: 1h/8h/24h/3d/7d/30d windows; local custom range and DST validation; current state independent of history; future forecasts clipped, no future actuals or ghost bars; conditional now marker; adaptive ticks; invalid inputs preserved; no bookings/quantities/audit writes.")
