"""Two-step fault reporting; synthetic SQLite only, no production/hardware."""
import runpy
import re
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_machine_control.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.production.models import TimeBooking,MachineControlCommand,DowntimeReason
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking
from uuid import uuid4

with app.app_context():
    admin=User.query.filter_by(username="test").one()
    machine=Machine(machine_no="FAULT-SELECT",machine_status="aktiv")
    active_reason=DowntimeReason(name="Werkzeugstörung",active=True)
    other_reason=DowntimeReason(name="Materialzufuhr",active=True)
    inactive_reason=DowntimeReason(name="NICHT-ANZEIGEN",active=False)
    db.session.add_all([machine,active_reason,other_reason,inactive_reason]);db.session.commit()
    def command(action,**kwargs):
        return execute(machine.id,admin.id,action,str(uuid4()),snapshot(machine.id)["revision"],**kwargs)
    command("setup",tool_no="W001")
    active=current_booking(machine.id)
    def client_for(user):
        client=app.test_client()
        with client.session_transaction() as session:session["_user_id"]=str(user.id);session["_fresh"]=True
        return client
    client=client_for(admin)
    panel=f"/production/machine/{machine.id}/control"
    path=panel+"/fault?embedded=1"
    def counts():return TimeBooking.query.count(),MachineControlCommand.query.count(),ChangeLog.query.count(),snapshot(machine.id)
    def fields(page):
        html=page.get_data(as_text=True)
        return {key:re.search(r'name="'+key+r'" value="([^"]+)"',html)[1] for key in ("access_csrf","command_id","revision")}
    before=counts()
    html=client.get(panel+"?embedded=1").get_data(as_text=True)
    assert 'name="reason_id"' not in html
    assert "Werkzeugstörung" not in html and "Materialzufuhr" not in html
    assert 'data-control-navigation' in html and '/control/fault?' in html
    assert client.get(path).status_code==200
    page=client.get(path);html=page.get_data(as_text=True)
    assert "Werkzeugstörung" in html and "Materialzufuhr" in html and "NICHT-ANZEIGEN" not in html
    assert 'type="radio" name="reason_id"' in html and "Abbrechen / zurück" in html
    assert counts()==before  # Opening and cancelling never closes the running setup.
    client.get(panel+"?embedded=1");assert counts()==before
    assert client.post(path,data={}).status_code==400
    payload={**fields(client.get(path)),"reason_id":"","comment":""}
    assert client.post(path,data=payload).status_code==400
    assert counts()==before
    payload={**fields(client.get(path)),"reason_id":inactive_reason.id,"comment":"Beschreibung bleibt erhalten"}
    response=client.post(path,data=payload)
    assert response.status_code==400 and "Beschreibung bleibt erhalten" in response.get_data(as_text=True)
    assert counts()==before
    # Even a former main-page fault POST only opens the selection step.
    payload={**fields(client.get(panel)),"action":"fault","reason_id":active_reason.id,"comment":"Noch nicht buchen"}
    response=client.post(panel,data=payload)
    assert response.status_code==303 and "/control/fault" in response.location and counts()==before
    # Selection opened against a stale main-page revision fails closed.
    old=snapshot(machine.id)["revision"]
    command("finish_setup")
    response=client.get(path+"&revision="+old)
    assert response.status_code==409 and 'name="reason_id"' in response.get_data(as_text=True)
    # Preserve iframe mode and never create a duplicate receipt on replay.
    payload={**fields(client.get(path)),"reason_id":active_reason.id,"comment":""}
    response=client.post(path,data=payload)
    assert response.status_code==303 and parse_qs(urlsplit(response.location).query)["embedded"]==["1"]
    assert current_booking(machine.id).process=="STOERUNG" and current_booking(machine.id).downtime_reason_id==active_reason.id
    total=counts()
    assert client.post(path,data=payload).status_code==303 and counts()==total
    command("clear_fault",comment="Werkzeug wurde geprüft")
    # Own description remains possible when there is no matching catalog reason.
    payload={**fields(client.get(path)),"reason_id":"","comment":"Sonstiger Defekt am Auswerfer"}
    assert client.post(path,data=payload).status_code==303
    assert current_booking(machine.id).downtime_reason_id is None
    assert current_booking(machine.id).comment=="Sonstiger Defekt am Auswerfer"
    command("clear_fault",comment="Auswerfer instandgesetzt")
    payload={**fields(client.get(path)),"reason_id":other_reason.id,"comment":""}
    command("maintenance",comment="Kontrolle der Maschine")
    assert client.post(path,data=payload).status_code==409
    assert current_booking(machine.id).process=="WARTUNG"
    # Reading the machine is not enough to open or submit fault selection.
    view=Permission.query.filter_by(name="production.view").one()
    role=Role(name="fault-view-only",active=True,permissions=[view])
    reader=User(username="fault-view-only",password_hash="unused",active=True,role=role)
    db.session.add(reader);db.session.commit()
    restricted=client_for(reader)
    assert restricted.get(panel).status_code==200
    assert restricted.get(path).status_code==403
    assert restricted.post(path,data=payload).status_code==403
    assert app.test_client().get(path).status_code==302
    assert "no-store" in client.get(path).headers["Cache-Control"]
print("PASS: no fault reasons on main panel; dedicated touch selection; navigation/cancel read-only; CSRF/rights/stale-state checks; inactive reasons rejected; reason or own description; embedded redirect; exactly-once fault confirmation.")
