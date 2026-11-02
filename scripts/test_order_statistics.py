"""Read-only metrics and audited start corrections with an isolated database."""
import runpy
import sys
import re
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.materials.models import Material
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking,QuantityReport
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.order_statistics import order_statistics
from factoryos.modules.production.services.order_statistics import working_seconds
from factoryos.modules.sampling.models import SamplingOrder
from types import SimpleNamespace
from factoryos.modules.production.services.booking_time_service import parse_local_start,correction_plan,revision,apply_correction
from scripts.upgrade_order_statistics import run_upgrade

for stamp,fold in [("2026-03-29T02:30",""),("2026-10-25T02:30","")]:
    try:parse_local_start(stamp,fold)
    except ValueError:pass
    else:raise AssertionError("DST ambiguity/nonexistent time accepted")
assert parse_local_start("2026-10-25T02:30","1")-parse_local_start("2026-10-25T02:30","0")==timedelta(hours=1)
assert parse_local_start("2026-11-02T11:00") == datetime(2026,11,2,10)
settings=SimpleNamespace(week_start_day=0,week_start_time="04:30",week_end_day=5,week_end_time="06:00")
interval=[(datetime(2026,11,7,5,30),datetime(2026,11,9,5))]
assert working_seconds(interval,settings,[])==3600
holiday=SimpleNamespace(start_at=datetime(2026,11,9),end_at=datetime(2026,11,10),title="Feiertag")
assert working_seconds(interval,settings,[holiday])==1800

with app.app_context():
    user=db.session.merge(fixture["user"])
    machine=Machine(machine_no="STATS-MACHINE",machine_status="aktiv")
    tool=Tool(tool_no="STATS-TOOL",name="Stats",cavities=2)
    batch_material=Material(material_no="STATS-BATCH",name="Farbe",material_type="masterbatch")
    article=Article(article_no="STATS-ARTICLE",article_name="Stats",cycle_time_s=999,shot_weight_g=40,
                    masterbatch=batch_material,masterbatch_percent=2,tools=[tool])
    order=Order(order_no="STATS-ORDER",article=article.article_no,tool_no=tool.tool_no,
                target_qty=600,cycle_time_s=60,status="in_arbeit")
    db.session.add_all([machine,article,order]);db.session.flush()
    free=TimeBooking(user_id=user.id,machine_id=machine.id,type="START",process="FREI",
                     start_time=datetime(2026,11,2,8),end_time=datetime(2026,11,2,12))
    booking=TimeBooking(user_id=user.id,machine_id=machine.id,order_id=order.id,type="START",
                        process="PROD",tool_no=tool.tool_no,start_time=datetime(2026,11,2,12))
    db.session.add_all([free,booking]);db.session.commit()
    run_upgrade(True);run_upgrade();run_upgrade()
    reader_role=Role(name="statistics-reader",active=True,permissions=[
        Permission(name="orders.view"),Permission(name="production.view")])
    reader=User(username="statistics-reader",password_hash="unused",active=True,role=reader_role)
    db.session.add(reader);db.session.commit()
    assert not any(p.name=="production.edit_booking_time" for p in reader.role.permissions)
    def client_for(person):
        client=app.test_client()
        with client.session_transaction() as session:session["_user_id"]=str(person.id);session["_fresh"]=True
        return client
    client=client_for(user);restricted=client_for(reader)
    now=datetime(2026,11,2,12,30)
    before_logs=ChangeLog.query.count()
    stats=order_statistics(order,now)
    assert stats["report_count"]==0 and stats["good"]==0
    assert stats["eta"]==datetime(2026,11,2,17) and stats["forecast"]["estimated_good_qty"]==60
    assert stats["total_mass"]==12 and stats["remaining_mass"]==12 and stats["consumed_estimate"] is None
    assert abs(stats["main_mass"]-12/1.02)<1e-9
    assert abs(stats["batch_mass"]-(12-12/1.02))<1e-9
    assert QuantityReport.query.count()==0 and ChangeLog.query.count()==before_logs
    html=client.get(f"/orders/{order.id}").get_data(as_text=True)
    assert "Materialbedarf" in html and "Startzeit der laufenden Buchung korrigieren" in html
    assert "Startzeit der laufenden Buchung korrigieren" not in restricted.get(f"/orders/{order.id}").get_data(as_text=True)
    path=f"/production/booking/{booking.id}/start-time"
    assert restricted.get(path).status_code==403
    assert restricted.post(path,data={}).status_code==403
    assert app.test_client().get(path).status_code==302
    page=client.get(path);assert page.status_code==200
    html=page.get_data(as_text=True)
    token=re.search(r'name="access_csrf" value="([^"]+)"',html)[1]
    rev=re.search(r'name="revision" value="([^"]+)"',html)[1]
    payload={"access_csrf":token,"revision":rev,"start_time":"2026-11-02T11:00:00",
             "reason":"Produktion lief bereits zwei Stunden früher","fold":""}
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={**payload,"intent":"commit"}).status_code==400
    assert client.post(path,data={**payload,"intent":"preview"}).status_code==200
    db.session.refresh(booking);db.session.refresh(free)
    assert booking.start_time==datetime(2026,11,2,12) and free.end_time==datetime(2026,11,2,12)
    assert client.post(path,data={**payload,"intent":"commit"}).status_code==302
    db.session.refresh(booking);db.session.refresh(free)
    assert booking.start_time==datetime(2026,11,2,10) and free.end_time==datetime(2026,11,2,10)
    stats=order_statistics(order,now)
    assert stats["eta"]==datetime(2026,11,2,15) and stats["working_seconds"]==9000
    assert stats["good"]==0 and QuantityReport.query.count()==0
    log=ChangeLog.query.filter_by(entity_type="order",entity_id=order.id).order_by(ChangeLog.id.desc()).first()
    assert log.user_id==user.id and "zwei Stunden" in log.changes["booking_start_correction"]["reason"]
    assert log.changes["booking_start_correction"]["free_intervals"][0]["booking_id"]==free.id
    # Latest report anchors the forecast; prior elapsed cycles are not counted again.
    report=QuantityReport(user_id=user.id,order_id=order.id,machine_id=machine.id,
                          good_qty=100,scrap_qty=20,created_at=datetime(2026,11,2,12))
    db.session.add(report);db.session.commit()
    stats=order_statistics(order,now)
    assert stats["good"]==100 and stats["scrap"]==20 and stats["remaining"]==500
    assert stats["eta"]==datetime(2026,11,2,16,10)
    assert abs(stats["consumed_estimate"]-2.4)<1e-9 and stats["remaining_mass"]==10
    # A real prior production interval cannot be overwritten by a backdate.
    other=Order(order_no="STATS-OTHER",target_qty=1,cycle_time_s=60)
    db.session.add(other);db.session.flush()
    conflict=TimeBooking(user_id=user.id,order_id=other.id,machine_id=machine.id,type="START",process="RUEST",
        start_time=datetime(2026,11,2,7),end_time=datetime(2026,11,2,8))
    db.session.add(conflict);db.session.commit()
    for stamp in (datetime(2026,11,2,7,30),datetime.utcnow()+timedelta(days=1)):
        try:correction_plan(booking,stamp,"Begründete Startkorrektur")
        except ValueError:pass
        else:raise AssertionError("Overlap/future accepted")
    # A new related event after preview invalidates the confirmation.
    html=client.get(path).get_data(as_text=True)
    rev=re.search(r'name="revision" value="([^"]+)"',html)[1]
    payload.update(revision=rev,start_time="2026-11-02T10:00:00")
    assert client.post(path,data={**payload,"intent":"preview"}).status_code==200
    added=TimeBooking(user_id=user.id,machine_id=machine.id,process="PAUSE",type="PAUSE",
        start_time=datetime(2026,11,2,6),end_time=datetime(2026,11,2,6,30))
    db.session.add(added);db.session.commit()
    assert client.post(path,data={**payload,"intent":"commit"}).status_code==409
    db.session.refresh(booking);assert booking.start_time==datetime(2026,11,2,10)
    # Explicitly granted permission works; it does not require the admin role.
    reader.role.permissions.append(Permission.query.filter_by(name="production.edit_booking_time").one());db.session.commit()
    assert restricted.get(path).status_code==200
    # Completely covered synthetic FREE phase is retained as an audited zero interval.
    html=client.get(path).get_data(as_text=True)
    payload.update(revision=re.search(r'name="revision" value="([^"]+)"',html)[1],start_time="2026-11-02T09:00:00")
    assert client.post(path,data={**payload,"intent":"preview"}).status_code==200
    assert client.post(path,data={**payload,"intent":"commit"}).status_code==302
    db.session.refresh(free)
    assert free.start_time==free.end_time==datetime(2026,11,2,8)
    # Even admin may not rewrite completed sampling records through booking corrections.
    completed=SamplingOrder.query.filter_by(state="completed").first()
    assert completed is not None
    protected=TimeBooking(user_id=user.id,order_id=completed.order_id,machine_id=machine.id,
        type="START",process="MUSTER",start_time=datetime(2026,11,1,8),end_time=datetime(2026,11,1,9))
    db.session.add(protected);db.session.commit()
    assert client.get(f"/production/booking/{protected.id}/start-time").status_code==400
    # Missing shot weight is unknown, not invented zero consumption.
    article.shot_weight_g=None;db.session.commit()
    assert order_statistics(order,now)["total_mass"] is None
    assert "Materialbedarf" in restricted.get(f"/orders/{order.id}").get_data(as_text=True)
print("PASS: audited/previewed start correction, permissions and explicit grants, CSRF, stale revision, overlap/future/DST protection, free interval adjustment, no quantity fabrication, time/report-based ETA, gross/net time and material/batch formulas.")
