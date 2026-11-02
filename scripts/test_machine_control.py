"""Isolated integration tests: app commands only, never production DB/hardware."""
import runpy
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,MachineControlState,MachineControlCommand,DowntimeReason
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking,ControlConflict,ControlDenied
from factoryos.modules.production.services.order_statistics import order_statistics
from scripts.upgrade_machine_control import run_upgrade

with app.app_context():
    admin=db.session.merge(fixture["user"])
    # Migration twice keeps bookings and grants unchanged.
    count_before=TimeBooking.query.count()
    grants={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    run_upgrade(True);run_upgrade();run_upgrade()
    assert TimeBooking.query.count()==count_before
    assert grants=={r.id:[p.name for p in r.permissions] for r in Role.query.all()}
    machine=Machine(machine_no="TOUCH-1",machine_status="aktiv")
    other=Machine(machine_no="TOUCH-2",machine_status="aktiv")
    order=Order(order_no="TOUCH-ORDER",article="A001",tool_no="W001",target_qty=100,cycle_time_s=30)
    db.session.add_all([machine,other,order]);db.session.commit()
    def run(action,m=machine,user=admin,**kwargs):
        return execute(m.id,user.id,action,str(uuid4()),snapshot(m.id)["revision"],**kwargs)
    def reject(action,m=machine,exception=ValueError,**kwargs):
        before=snapshot(m.id);total=MachineControlCommand.query.count()
        try:run(action,m=m,**kwargs)
        except exception:db.session.rollback()
        else:raise AssertionError(f"Unexpected accepted action: {action}")
        assert snapshot(m.id)==before and MachineControlCommand.query.count()==total
    reject("nonsense")
    reject("start")
    reject("setup")
    reject("start",order_id=str(2**100))
    reject("maintenance",comment="")
    reject("fault",reason_id="9999999")
    reject("fault",comment="x")
    run("setup",order_id=order.id)
    assert current_booking(machine.id).process=="RUEST"
    reject("start",order_id=order.id)
    run("finish_setup")
    assert current_booking(machine.id).process=="FREI" and order.status=="open"
    # Start and exactly-once retry, with a conflicting UUID rejected.
    command=str(uuid4());rev=snapshot(machine.id)["revision"]
    receipt,replayed=execute(machine.id,admin.id,"start",command,rev,order_id=order.id)
    assert not replayed
    total=TimeBooking.query.count();commands=MachineControlCommand.query.count()
    again,replayed=execute(machine.id,admin.id,"start",command,rev,order_id=order.id)
    assert replayed and again.id==receipt.id and TimeBooking.query.count()==total
    assert MachineControlCommand.query.count()==commands and order.status=="in_arbeit"
    try:execute(machine.id,admin.id,"start",command,rev,order_id=order.id,comment="anderer Inhalt")
    except ControlConflict:db.session.rollback()
    else:raise AssertionError("UUID changed payload accepted")
    reject("start",m=other,order_id=order.id,exception=ControlConflict)
    stale=snapshot(machine.id)["revision"]
    run("pause");assert current_booking(machine.id).process=="PAUSE"
    try:execute(machine.id,admin.id,"resume",str(uuid4()),stale)
    except ControlConflict:db.session.rollback()
    else:raise AssertionError("Stale version accepted")
    run("fault",comment="Störung während der Produktionspause")
    run("clear_fault",comment="Störung in Pause behoben")
    assert current_booking(machine.id).process=="PAUSE"
    run("resume");assert current_booking(machine.id).process=="PROD"
    before_fault=current_booking(machine.id)
    run("fault",comment="Kühlwasser fehlt")
    assert current_booking(machine.id).process=="STOERUNG" and current_booking(machine.id).order_id==order.id
    assert before_fault.end_time is not None
    assert MachineControlState.query.get(machine.id).resume_order_id==order.id
    assert order_statistics(order)["eta"] is None
    reject("resume")
    reject("start",m=other,order_id=order.id)
    reject("clear_fault",comment="")
    run("clear_fault",comment="Kühlwasser geprüft und freigegeben")
    assert current_booking(machine.id).process=="PAUSE"  # never auto restart
    run("resume");assert current_booking(machine.id).process=="PROD"
    reject("stop",comment="")
    run("stop",comment="Auftrag manuell unterbrochen")
    assert current_booking(machine.id).process=="FREI" and order.status!="fertig"
    for start,finish,process in [("maintenance","finish_maintenance","WARTUNG"),("other","finish_other","SONSTIG")]:
        run(start,comment="Geplante Tätigkeit an der Maschine")
        assert current_booking(machine.id).process==process
        run("fault",comment="Unterbrechung wegen Kühlung")
        run("clear_fault",comment="Ursache wurde behoben")
        assert current_booking(machine.id).process=="PAUSE"
        run("resume");assert current_booking(machine.id).process==process
        run(finish);assert current_booking(machine.id).process=="FREI"
    run("unsetup",tool_no="W001");run("fault",comment="Werkzeug lässt sich nicht lösen")
    run("clear_fault",comment="Verriegelung kontrolliert");run("resume")
    assert current_booking(machine.id).process=="ABRUEST"
    run("finish_setup")
    reason=DowntimeReason(name="Kühlung",active=True);db.session.add(reason);db.session.commit()
    run("fault",reason_id=reason.id);run("clear_fault",comment="Kühlung kontrolliert")
    assert current_booking(machine.id).process=="FREI"
    # Exact interval continuity, one open booking, full operator audit.
    bookings=TimeBooking.query.filter_by(machine_id=machine.id).order_by(TimeBooking.id).all()
    assert sum(b.end_time is None for b in bookings)==1
    for previous,following in zip(bookings,bookings[1:]):assert previous.end_time==following.start_time
    assert all(c.user_id==admin.id and c.source=="app" for c in MachineControlCommand.query.filter_by(machine_id=machine.id))
    assert ChangeLog.query.filter_by(entity_type="machine",entity_id=machine.id,user_id=admin.id).count()==MachineControlCommand.query.filter_by(machine_id=machine.id).count()
    # Inactive machines, invalid/locked orders and duplicate legacy records.
    machine.machine_status="inaktiv";db.session.commit()
    reject("start",order_id=order.id);reject("maintenance",comment="Planmäßige Wartung")
    machine.machine_status="aktiv";order.status="fertig";db.session.commit()
    reject("start",order_id=order.id)
    order.status="open";order.cycle_time_s=None;db.session.commit();reject("start",order_id=order.id)
    order.cycle_time_s=30;db.session.commit()
    duplicate=TimeBooking(user_id=admin.id,machine_id=machine.id,type="START",process="FREI")
    db.session.add(duplicate);db.session.commit()
    reject("start",order_id=order.id,exception=ControlConflict)
    duplicate.end_time=datetime.utcnow();db.session.commit()
    # Per-action rights and CSRF; old mutation endpoints are navigation only.
    view=Permission.query.filter_by(name="production.view").first()
    if not view:view=Permission(name="production.view");db.session.add(view)
    role=Role(name="touch-readonly",active=True,permissions=[view])
    reader=User(username="touch-reader",password_hash="unused",active=True,role=role)
    db.session.add(reader);db.session.commit()
    def client_for(user):
        client=app.test_client()
        with client.session_transaction() as session:session["_user_id"]=str(user.id);session["_fresh"]=True
        return client
    client=client_for(admin);restricted=client_for(reader)
    path=f"/production/machine/{machine.id}/control"
    assert app.test_client().get(path).status_code==302
    assert restricted.get(path).status_code==200
    def fields(client):
        html=client.get(path).get_data(as_text=True)
        return {name:re.search(r'name="'+name+r'" value="([^"]+)"',html)[1] for name in ("access_csrf","command_id","revision")}
    assert client.post(path,data={"action":"start"}).status_code==400
    payload={**fields(restricted),"action":"start","order_id":order.id}
    assert restricted.post(path,data=payload).status_code==403
    assert current_booking(machine.id).process=="FREI"
    payload={**fields(client),"action":"start","order_id":order.id}
    assert client.post(path,data=payload).status_code==303
    assert client.post(path,data=payload).status_code==303  # same command ID = no second booking
    assert current_booking(machine.id).process=="PROD"
    active=current_booking(machine.id)
    assert client.post(f"/projects/stop/{active.id}",data={"comment":"Bypassversuch"}).status_code==303
    assert current_booking(machine.id).id==active.id
    for suffix in (f"/end/{active.id}",f"/resume/{active.id}",f"/machine/{machine.id}/downtime",f"/machine/{machine.id}/event",f"/machine/{machine.id}/setup"):
        assert client.post("/production"+suffix,data={}).status_code==303
        assert current_booking(machine.id).id==active.id
    assert client.get(path+"/state").json["revision"]==snapshot(machine.id)["revision"]
    html=client.get("/production/booking").get_data(as_text=True)
    assert 'id="machine-control-dialog"' in html and 'data-machine-control-url=' in html
    # Explicit grants, not role names, enable actions; clear fault is separate.
    start=Permission.query.filter_by(name="production.start").first()
    if not start:start=Permission(name="production.start");db.session.add(start)
    role.permissions.append(start);db.session.commit()
    reject("fault",user=reader,comment="Produktion hat eine Störung",exception=ControlDenied)
    run("fault",comment="Hydraulik meldet Störung")
    payload={**fields(restricted),"action":"clear_fault","comment":"Ursache wurde behoben"}
    assert restricted.post(path,data=payload).status_code==403
    role.permissions.append(Permission.query.filter_by(name="production.clear_fault").one());db.session.commit()
    payload={**fields(restricted),"action":"clear_fault","comment":"Ursache wurde behoben"}
    assert restricted.post(path,data=payload).status_code==303
    assert current_booking(machine.id).process=="PAUSE"
    # Expired view must fail closed after a successful command by another user.
    stale_payload={**fields(client),"action":"resume"}
    run("resume",user=reader)
    assert client.post(path,data=stale_payload).status_code==409
    assert "no-store" in client.get(path).headers["Cache-Control"]
    # Order/machine deletion and terminal edits must not erase active history.
    token=fields(client)["access_csrf"]
    assert client.post(f"/orders/delete/{order.id}",data={"access_csrf":token}).status_code==302
    assert db.session.get(Order,order.id) is not None
    assert client.post(f"/masterdata/machines/{machine.id}/delete",data={"access_csrf":token}).status_code==302
    assert db.session.get(Machine,machine.id) is not None
    assert client.post(f"/orders/edit/{order.id}",data={"article":order.article,"status":"fertig","cycle_time_s":"30","target_qty":"100"}).status_code==400
    db.session.refresh(order);assert order.status!="fertig"
    # Any late audit/storage failure must roll back the booking and receipt too.
    from sqlalchemy import event
    before=snapshot(machine.id);total=TimeBooking.query.count()
    def fail_audit(*args):raise RuntimeError("synthetic audit failure")
    event.listen(ChangeLog,"before_insert",fail_audit)
    try:
        try:run("pause")
        except RuntimeError:db.session.rollback()
        else:raise AssertionError("Injected audit failure did not abort")
    finally:event.remove(ChangeLog,"before_insert",fail_audit)
    assert snapshot(machine.id)==before and TimeBooking.query.count()==total
print("PASS: atomic state transitions, setup/fault/maintenance recovery, no automatic restart, exact-once UUID replay, stale revisions, order reservations, permissions/CSRF, legacy navigation, audit, timeline popup, interval continuity and non-destructive upgrades.")
