"""Queues and forecasts use a synthetic DB; never production/hardware."""
import runpy
from pathlib import Path
from datetime import datetime,timedelta
from uuid import uuid4
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_machine_control.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.production.models import (ProductionPlanEntry,ProductionPlanningState,MachinePlanningSettings,
    TimeBooking,QuantityReport,MachineControlCommand)
from factoryos.modules.production.services.planning_service import modify_plan,planning_version,queue,build_schedule
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking,ControlConflict,ControlDenied
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from factoryos.core.models.change_log import ChangeLog
from scripts.upgrade_order_planning import run_upgrade

with app.app_context():
    admin=User.query.filter_by(username="test").one()
    # Upgrade from pre-existing tables with no planning schema; repeat safely.
    from sqlalchemy import inspect
    for model in (ProductionPlanEntry,MachinePlanningSettings,ProductionPlanningState):model.__table__.drop(bind=db.engine)
    before=TimeBooking.query.count(),QuantityReport.query.count()
    grants={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    run_upgrade(True);assert not inspect(db.engine).has_table("production_plan_entries")
    run_upgrade();run_upgrade()
    assert before==(TimeBooking.query.count(),QuantityReport.query.count())
    assert grants=={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    machines=[Machine(machine_no=f"PLAN-{i}",machine_status="aktiv") for i in range(3)]
    tool=Tool(tool_no="PLAN-TOOL",name="Plan",cavities=2)
    orders=[Order(order_no=f"PLAN-{i}",tool_no=tool.tool_no,target_qty=120,cycle_time_s=60,status="open") for i in range(6)]
    db.session.add_all([*machines,tool,*orders]);db.session.commit()
    m1,m2,m3=machines;o1,o2,o3,o4,o5,o6=orders
    def change(action,m=m1,entry=None,user=admin,**kwargs):
        return modify_plan(user.id,planning_version(),action,m.id,entry.id if entry else None,**kwargs)
    def rejected(action,m=m1,entry=None,exception=ValueError,**kwargs):
        version=planning_version();ids=[(e.id,e.machine_id,e.position,e.state) for e in ProductionPlanEntry.query.all()]
        try:change(action,m,entry,**kwargs)
        except exception:db.session.rollback()
        else:raise AssertionError(f"Invalid command accepted: {action}")
        assert planning_version()==version and ids==[(e.id,e.machine_id,e.position,e.state) for e in ProductionPlanEntry.query.all()]
    change("add",order_id=o1.id,setup_minutes=10)
    change("add",order_id=o2.id)
    e1,e2=queue(m1.id)
    assert [e.order_id for e in queue(m1.id)]==[o1.id,o2.id]
    rejected("add",order_id=o1.id,m=m2,exception=ControlConflict)
    rejected("add",order_id=o3.id,setup_minutes=-1)
    change("up",entry=e2);assert queue(m1.id)[0].id==e2.id
    change("down",entry=e2);assert queue(m1.id)[0].id==e1.id
    change("reorder",ordered_ids=[e2.id,e1.id]);assert queue(m1.id)[0].id==e2.id
    rejected("reorder",ordered_ids=[e1.id,e1.id])
    change("reorder",ordered_ids=[e1.id,e2.id])
    now=datetime(2026,11,2,8)
    def lane(schedule,m=m1):return next(l for l in schedule["machines"] if l["machine"].id==m.id)
    def counts():return tuple(model.query.count() for model in (TimeBooking,QuantityReport,MachineControlCommand,ChangeLog))
    before=counts();rows=lane(build_schedule(now))["rows"]
    assert rows[0]["setup_start"]==now and rows[0]["start"]==now+timedelta(minutes=10)
    assert rows[0]["end"]==now+timedelta(minutes=70) and rows[1]["start"]==rows[0]["end"]
    assert rows[1]["end"]==now+timedelta(minutes=130) and counts()==before
    # Only confirmed quantities reduce a queued order's remaining duration.
    report=QuantityReport(user_id=admin.id,machine_id=m1.id,order_id=o1.id,good_qty=20,scrap_qty=5)
    db.session.add(report);db.session.commit()
    assert lane(build_schedule(now))["rows"][0]["seconds"]==3000
    # Shutdown + bridge day are skipped in both setup and production.
    change("update",entry=e1,setup_minutes=0,not_before=datetime(2026,11,7,5,30))
    holiday=SimpleNamespace(start_at=datetime(2026,11,9),end_at=datetime(2026,11,10),title="Brückentag")
    rows=lane(build_schedule(now,exceptions=[holiday]))["rows"]
    assert rows[0]["end"]==datetime(2026,11,10,0,20)
    change("update",entry=e1,setup_minutes=10)
    # Conflict warnings across machines; no invented resource resolution.
    change("add",m=m2,order_id=o3.id)
    sched=build_schedule(now)
    assert any("zeitgleich" in w for w in lane(sched)["rows"][0]["warnings"])
    # Change machine, and removal archives rather than deletes.
    change("transfer",entry=e2,target_machine_id=m3.id)
    assert queue(m3.id)[0].id==e2.id and len(queue(m1.id))==1
    change("remove",m=m3,entry=e2);assert e2.state=="cancelled" and db.session.get(Order,o2.id)
    legacy_fault=TimeBooking(user_id=admin.id,machine_id=m2.id,prev_order_id=o2.id,
        process="STOERUNG",type="START",start_time=now-timedelta(minutes=10))
    db.session.add(legacy_fault);db.session.commit()
    rejected("add",m=m3,order_id=o2.id)
    legacy_fault.end_time=now;db.session.commit()
    # Unknown current machine end blocks all downstream rows until an explicit future assumption.
    busy=TimeBooking(user_id=admin.id,machine_id=m1.id,process="STOERUNG",type="START",start_time=now-timedelta(hours=1))
    db.session.add(busy);db.session.commit()
    assert lane(build_schedule(now))["rows"][0]["start"] is None
    rejected("availability",available_from=now+timedelta(hours=1),availability_note="x")
    change("availability",available_from=now+timedelta(hours=1),availability_note="Instandhaltung erwartet Freigabe")
    assert lane(build_schedule(now))["rows"][0]["setup_start"]==now+timedelta(hours=1)
    # An expired assumption must not silently free an ongoing fault.
    assert lane(build_schedule(now+timedelta(hours=2)))["rows"][0]["start"] is None
    busy.end_time=now;db.session.commit()
    change("availability",available_from=None,availability_note="")
    # Queue start is explicit, ordered, machine-bound, atomic with command receipt.
    def command(action,m=m1,**kwargs):
        return execute(m.id,admin.id,action,str(uuid4()),snapshot(m.id)["revision"],**kwargs)
    try:command("start",order_id=o1.id,m=m3)
    except ControlConflict:db.session.rollback()
    else:raise AssertionError("Wrong machine started queued order")
    change("add",order_id=o4.id)
    try:command("start",order_id=o4.id)
    except ControlConflict:db.session.rollback()
    else:raise AssertionError("Out-of-sequence start accepted")
    prior_version=planning_version();command("start",order_id=o1.id)
    assert e1.state=="started" and e1.started_booking_id==current_booking(m1.id).id
    assert planning_version()==prior_version+1 and queue(m1.id)[0].order_id==o4.id
    # Current ETA precedes the next queued order; fault makes that end unknown.
    real_now=datetime.utcnow()
    sched=build_schedule(real_now);next_row=lane(sched)["rows"][0]
    assert next_row["start"] and next_row["start"]>real_now
    command("fault",comment="Störung in laufender Fertigung")
    assert lane(build_schedule())["rows"][0]["start"] is None
    command("clear_fault",comment="Störung vollständig behoben");command("resume")
    # Timeline plan bars are separate from TimeBooking and exclude shutdown slices.
    before=counts();timeline=get_machine_timeline("30d")
    all_items=[i for l in timeline["lanes"] for i in l["items"]]
    assert any(i["kind"]=="planned" for i in all_items) and counts()==before
    assert all(0<=i["left"]<=100 and 0<i["width"]<=100-i["left"]+1e-8 for i in all_items)
    # Stale version never overwrites another planner.
    stale=planning_version();change("add",m=m3,order_id=o5.id)
    try:modify_plan(admin.id,stale,"add",m3.id,order_id=o6.id)
    except ControlConflict:db.session.rollback()
    else:raise AssertionError("Stale planning version accepted")
    # Fail the audit at the end: all changes must roll back.
    from sqlalchemy import event
    total=ProductionPlanEntry.query.count();version=planning_version()
    def fail(*args):raise RuntimeError("synthetic audit failure")
    event.listen(ChangeLog,"before_insert",fail)
    try:
        try:change("add",m=m3,order_id=o6.id)
        except RuntimeError:db.session.rollback()
        else:raise AssertionError("Injected failure did not abort")
    finally:event.remove(ChangeLog,"before_insert",fail)
    assert ProductionPlanEntry.query.count()==total and planning_version()==version
    # UI, CSRF, read-only view, explicit permission grant and delete protections.
    def client_for(user):
        c=app.test_client()
        with c.session_transaction() as session:session["_user_id"]=str(user.id);session["_fresh"]=True
        return c
    client=client_for(admin);page=client.get("/production/planning")
    assert page.status_code==200
    html=page.get_data(as_text=True)
    assert "Auftragsplanung" in html and 'draggable="true"' in html and "Fertig · geschätzt" in html
    import re
    token=re.search(r'name="access_csrf" value="([^"]+)"',html)[1]
    payload=dict(action="add",machine_id=m3.id,order_id=o6.id,version=str(planning_version()),access_csrf=token)
    assert client.post("/production/planning",data={}).status_code==400
    assert client.post("/production/planning",data=payload).status_code==303
    assert client.post("/production/planning",data=payload).status_code==409
    view=Permission.query.filter_by(name="production.view").one()
    reader=User(username="planning-reader",password_hash="unused",active=True,role=Role(name="planning-reader",active=True,permissions=[view]))
    db.session.add(reader);db.session.commit();restricted=client_for(reader)
    assert restricted.get("/production/planning").status_code==200
    assert 'draggable="true"' not in restricted.get("/production/planning").get_data(as_text=True)
    assert restricted.post("/production/planning",data=payload).status_code==403
    reader.role.permissions.append(Permission.query.filter_by(name="production.plan").one());db.session.commit()
    granted=restricted.get("/production/planning").get_data(as_text=True)
    assert 'draggable="true"' in granted
    assert 'id="planning-drag-transfer"' in granted
    assert app.test_client().get("/production/planning").status_code==302
    assert client.post(f"/orders/delete/{o6.id}",data={"access_csrf":token}).status_code==302
    assert db.session.get(Order,o6.id) is not None
    assert client.post(f"/masterdata/machines/{m3.id}/delete",data={"access_csrf":token}).status_code==302
    assert db.session.get(Machine,m3.id) is not None
    assert "planned-production" in client.get("/production/booking?zeitraum=30d").get_data(as_text=True)
    # An inactive source can still be unplanned; no trap holding its queued orders.
    m3.machine_status="inaktiv";db.session.commit()
    change("remove",m=m3,entry=queue(m3.id)[0])
    m3.machine_status="aktiv";db.session.commit()
    head=queue(m3.id)[0];version=planning_version();before=counts();state=snapshot(m3.id)
    event.listen(ChangeLog,"before_insert",fail)
    try:
        try:command("start",m=m3,order_id=head.order_id)
        except RuntimeError:db.session.rollback()
        else:raise AssertionError("Failed audit left a partial planned start")
    finally:event.remove(ChangeLog,"before_insert",fail)
    assert head.state=="queued" and planning_version()==version and counts()==before and snapshot(m3.id)==state
print("PASS: persisted machine queues, append/reorder/transfer/archive, strict quantities/cycle, setup and shutdown/holiday forecasts, resource warnings, blocked unknown ends and explicit availability, atomic ordered manual start, stale versions, rollback, permissions/CSRF, read-only timeline, migration twice and delete protection.")
