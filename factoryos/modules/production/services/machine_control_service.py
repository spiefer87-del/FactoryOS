"""Authoritative, transactional machine commands. No hardware actuation.

Future device adapters must authenticate a device/operator, bind its machine,
then call this service. There is deliberately no unauthenticated device API.
"""
import hashlib
import json
from uuid import UUID
from datetime import datetime
from sqlalchemy import update
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.models.change_log import ChangeLog
from factoryos.models.machine import Machine
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import (
    TimeBooking, DowntimeReason, MachineControlLock, MachineControlState, MachineControlCommand,
)

LABELS = {"FREI":"Bereit / frei", "PROD":"Produktion", "MUSTER":"Musterung",
          "RUEST":"Rüsten", "ABRUEST":"Abrüsten", "PAUSE":"Unterbrochen / bereit zum Fortsetzen",
          "STOERUNG":"Störung", "WARTUNG":"Wartung", "SONSTIG":"Sonstiger Vorgang"}
ACTIONS = {
    "start":"Auftrag starten", "pause":"Produktion pausieren", "resume":"Vorgang fortsetzen",
    "stop":"Vorgang stoppen", "setup":"Rüsten starten", "unsetup":"Abrüsten starten",
    "finish_setup":"Rüsten beenden", "fault":"Störung melden", "clear_fault":"Entstören",
    "maintenance":"Wartung starten", "finish_maintenance":"Wartung beenden",
    "other":"Sonstigen Vorgang starten", "finish_other":"Sonstigen Vorgang beenden",
}
PERMISSIONS = {"start":"production.start", "pause":"production.stop", "resume":"production.view",
    "stop":"production.stop", "setup":"production.setup", "unsetup":"production.setup",
    "finish_setup":"production.setup", "fault":"production.stop", "clear_fault":"production.clear_fault",
    "maintenance":"production.maintenance", "finish_maintenance":"production.maintenance",
    "other":"production.events", "finish_other":"production.events"}
TERMINAL = {"fertig", "finished", "gesperrt", "locked", "cancelled", "canceled", "storniert", "abgeschlossen"}


class ControlConflict(ValueError):
    pass


class ControlDenied(ValueError):
    pass


def acquire_control_lock():
    # Single serialization point also prevents one order starting on two machines.
    # INSERT ... ON CONFLICT avoids a first-request race on a fresh installation.
    dialect = db.engine.dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    elif dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        raise ControlConflict("Maschinensteuerung unterstützt diese Datenbank noch nicht.")
    db.session.execute(insert(MachineControlLock).values(id=1, version=0).on_conflict_do_nothing(index_elements=["id"]))
    db.session.execute(update(MachineControlLock).where(MachineControlLock.id==1).values(version=MachineControlLock.version+1))
    db.session.expire_all()


def snapshot(machine_id):
    state = db.session.get(MachineControlState, machine_id)
    active = TimeBooking.query.filter_by(machine_id=machine_id,end_time=None).order_by(TimeBooking.id).all()
    value = {"version":state.version if state else 0,
             "resume_process":state.resume_process if state else None,
             "resume_order_id":state.resume_order_id if state else None,
             "resume_tool_no":state.resume_tool_no if state else None,
             "active":[{"id":b.id,"process":b.process,"type":b.type,"order_id":b.order_id,
                        "tool_no":b.tool_no,"start":b.start_time.isoformat(),
                        "prev_order_id":b.prev_order_id,"reason_id":b.downtime_reason_id} for b in active]}
    value["revision"] = hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return value


def current_booking(machine_id):
    return TimeBooking.query.filter_by(machine_id=machine_id,end_time=None).order_by(TimeBooking.id).first()


def available_actions(process, state=None):
    if process == "FREI": return ["start","setup","unsetup","maintenance","other","fault"]
    if process in ("PROD","MUSTER"): return ["pause","fault","stop"]
    if process == "STOERUNG": return ["clear_fault"]
    if process == "PAUSE": return ["resume","fault","stop"]
    if process in ("RUEST","ABRUEST"): return ["finish_setup","fault","stop"]
    if process == "WARTUNG": return ["finish_maintenance","fault","stop"]
    if process == "SONSTIG": return ["finish_other","fault","stop"]
    return ["stop"]  # Legacy unknown process: explicitly end, never silently replace.


def _order(order_id, machine_id, ignore_booking_id=None):
    order = db.session.get(Order, int(order_id)) if order_id else None
    if not order or order.is_project or (order.status or "").lower() in TERMINAL:
        raise ValueError("Bitte einen offenen Fertigungs- oder Musterungsauftrag auswählen.")
    if order.sampling:
        if order.sampling.state not in ("in_progress","review") or order.sampling.machine_id!=machine_id:
            raise ValueError("Musterung muss in Bearbeitung/Prüfung und dieser Maschine zugeordnet sein.")
    # Positive cycle time is mandatory even for legacy orders before starting.
    from math import isfinite
    try: cycle=float(order.cycle_time_s)
    except (TypeError, ValueError): cycle=0
    if not isfinite(cycle) or cycle<=0:
        raise ValueError("Im Auftrag fehlt eine gültige Soll-Zykluszeit. Bitte zuerst ergänzen.")
    if not order.target_qty or order.target_qty<=0:
        raise ValueError("Im Auftrag fehlt eine positive Sollmenge. Bitte zuerst ergänzen.")
    active = TimeBooking.query.filter_by(order_id=order.id,end_time=None).all()
    if any(b.id!=ignore_booking_id for b in active):
        raise ControlConflict("Der Auftrag ist bereits aktiv oder auf einer Maschine reserviert.")
    reserved = MachineControlState.query.filter_by(resume_order_id=order.id).all()
    if any(s.machine_id!=machine_id for s in reserved):
        raise ControlConflict("Der unterbrochene Auftrag ist noch auf einer anderen Maschine reserviert.")
    return order


def execute(machine_id, user_id, action, command_id, expected_revision, *, order_id=None,
            tool_no=None, reason_id=None, comment="", commit=True):
    """Execute once. Caller rolls back on ALL exceptions; optional outer transaction.

    expected_revision + UUID are required even for future device adapters.
    User identity must come from trusted authentication, never request payload.
    """
    user = db.session.get(User,user_id)
    if action not in ACTIONS: raise ValueError("Unbekannter Maschinenbefehl.")
    if not has_permission(user,PERMISSIONS[action]): raise ControlDenied("Keine Berechtigung für diese Aktion.")
    try:
        if str(UUID(command_id))!=command_id: raise ValueError()
    except (ValueError,TypeError,AttributeError): raise ValueError("Ungültige Befehlskennung. Bitte neu laden.")
    comment=(comment or "").strip()
    if len(comment)>255: raise ValueError("Kommentar darf höchstens 255 Zeichen enthalten.")
    try:
        order_id=int(order_id) if order_id else None
        reason_id=int(reason_id) if reason_id else None
    except (ValueError,TypeError): raise ValueError("Ungültige Auftrags- oder Störgrundauswahl.")
    if any(value is not None and not 1<=value<2**63 for value in (order_id,reason_id)):
        raise ValueError("Ungültige Auftrags- oder Störgrundauswahl.")
    tool_no=(tool_no or "").strip() or None
    payload=dict(action=action,order_id=order_id,tool_no=tool_no,reason_id=reason_id,
                 comment=comment,revision=expected_revision)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    acquire_control_lock()
    user=db.session.get(User,user_id)
    if not has_permission(user,PERMISSIONS[action]): raise ControlDenied("Berechtigung wurde inzwischen geändert.")
    machine=db.session.get(Machine,machine_id)
    if not machine: raise ValueError("Maschine nicht gefunden.")
    receipt=MachineControlCommand.query.filter_by(command_id=command_id).first()
    if receipt:
        if receipt.machine_id!=machine_id or receipt.user_id!=user_id or receipt.payload_hash!=digest:
            raise ControlConflict("Befehlskennung wurde bereits für einen anderen Inhalt benutzt.")
        if commit: db.session.commit()
        return receipt, True
    before=snapshot(machine_id)
    if not expected_revision or before["revision"]!=expected_revision:
        raise ControlConflict("Maschinenstand wurde inzwischen geändert. Bitte neu laden und erneut entscheiden.")
    if len(before["active"])>1:
        raise ControlConflict("Mehrere aktive Altbuchungen: keine automatische Bereinigung. Bitte Administration informieren.")
    active=current_booking(machine_id)
    process=active.process if active else "FREI"
    if action not in available_actions(process):
        raise ControlConflict("Dieser Befehl passt nicht zum aktuellen Maschinenzustand.")
    if machine.machine_status!="aktiv" and action in ("start","setup","unsetup","maintenance","other","resume"):
        raise ValueError("Maschine ist im Stammdatensatz nicht aktiv.")
    state=db.session.get(MachineControlState,machine_id)
    if not state:
        state=MachineControlState(machine_id=machine_id,version=0);db.session.add(state)
    next_process="FREI";next_order=None;next_tool=None;reason=None
    def remember(p,o,t):
        state.resume_process=p;state.resume_order_id=o;state.resume_tool_no=t
    def forget(): remember(None,None,None)
    if action in ("start","setup","unsetup"):
        order=_order(order_id,machine_id) if order_id else None
        if action=="start" and not order: raise ValueError("Bitte Auftrag auswählen.")
        next_tool=tool_no or (order.tool_no if order else None)
        if action in ("setup","unsetup") and not next_tool:
            raise ValueError("Bitte Werkzeugnummer für den Rüstvorgang auswählen.")
        if next_tool and not Tool.query.filter_by(tool_no=next_tool).first():
            raise ValueError("Werkzeugnummer ist nicht in den Stammdaten vorhanden.")
        if order and action=="start" and tool_no and order.tool_no and tool_no!=order.tool_no:
            raise ValueError("Werkzeug widerspricht dem Auftrag. Bitte Zuordnung im Auftrag prüfen.")
        next_process=("MUSTER" if order.sampling else "PROD") if action=="start" else "RUEST" if action=="setup" else "ABRUEST"
        next_order=order.id if order else None
        forget()
        if order and action=="start" and (order.status or "").lower() in ("open","offen"):
            order.status="in_arbeit"
    elif action=="pause":
        remember(process,active.order_id,active.tool_no)
        next_process="PAUSE";next_order=active.order_id;next_tool=active.tool_no
    elif action=="fault":
        if reason_id:
            reason=db.session.get(DowntimeReason,reason_id)
            if not reason or not reason.active: raise ValueError("Störgrund ist nicht mehr aktiv.")
        if not reason and len(comment)<5: raise ValueError("Bitte Störgrund wählen oder Störung mit mindestens 5 Zeichen beschreiben.")
        if process not in ("PAUSE","FREI"): remember(process,active.order_id,active.tool_no)
        elif process=="PAUSE" and not state.resume_process:
            remember("MUSTER" if active.order and active.order.sampling else "PROD",active.order_id,active.tool_no)
        elif process=="FREI": forget()
        next_process="STOERUNG";next_order=state.resume_order_id;next_tool=active.tool_no if active else None
    elif action=="clear_fault":
        if len(comment)<5: raise ValueError("Bitte Behebung der Störung kurz beschreiben (mindestens 5 Zeichen).")
        if not state.resume_process and active.prev_order_id:
            previous=db.session.get(Order,active.prev_order_id)
            if previous: remember("MUSTER" if previous.sampling else "PROD",previous.id,active.tool_no)
        # Acknowledgement NEVER starts production. A separate resume is required.
        next_process="PAUSE" if state.resume_process else "FREI"
        next_order=state.resume_order_id;next_tool=state.resume_tool_no
    elif action=="resume":
        resume=state.resume_process
        oid=state.resume_order_id
        if not resume and active.order_id:
            resume="MUSTER" if active.order and active.order.sampling else "PROD";oid=active.order_id
        if resume not in ("PROD","MUSTER","RUEST","ABRUEST","WARTUNG","SONSTIG"):
            raise ValueError("Kein eindeutiger fortsetzbarer Vorgang. Bitte stoppen und neu zuordnen.")
        required="production.setup" if resume in ("RUEST","ABRUEST") else "production.maintenance" if resume=="WARTUNG" else "production.events" if resume=="SONSTIG" else "production.start"
        if not has_permission(user,required): raise ControlDenied("Für den vorherigen Vorgang fehlt die Berechtigung.")
        order=_order(oid,machine_id,active.id) if oid else None
        if resume in ("PROD","MUSTER") and not order: raise ValueError("Auftragsbezug fehlt. Bitte stoppen und neu starten.")
        next_process=resume;next_order=oid;next_tool=state.resume_tool_no or active.tool_no
        if order and (order.status or "").lower() in ("open","offen"): order.status="in_arbeit"
        forget()
    elif action in ("maintenance","other"):
        if len(comment)<5: raise ValueError("Bitte Tätigkeit kurz beschreiben (mindestens 5 Zeichen).")
        next_process="WARTUNG" if action=="maintenance" else "SONSTIG";forget()
    else:
        if action=="stop" and len(comment)<5: raise ValueError("Bitte Grund für das Stoppen angeben (mindestens 5 Zeichen).")
        # Ending setup just frees the machine. Production always needs its own start.
        forget()
    now=datetime.utcnow()
    if active:
        if active.start_time>now: raise ControlConflict("Aktive Buchung liegt in der Zukunft. Zeitbasis zuerst korrigieren.")
        active.end_time=now
    booking=TimeBooking(user_id=user_id,machine_id=machine_id,order_id=next_order,process=next_process,
        type="PAUSE" if next_process=="PAUSE" else "START",start_time=now,tool_no=next_tool,
        downtime_reason_id=reason.id if reason else None,
        prev_order_id=state.resume_order_id if next_process=="STOERUNG" else None,comment=comment or None)
    db.session.add(booking);state.version+=1;db.session.flush()
    after=snapshot(machine_id)
    receipt=MachineControlCommand(command_id=command_id,machine_id=machine_id,user_id=user_id,
        source="app",action=action,payload_hash=digest,comment=comment or None,before_state=before,after_state=after)
    db.session.add(receipt)
    affected={item["order_id"] for item in before["active"] if item["order_id"]}
    affected.update(oid for oid in (next_order,before["resume_order_id"],state.resume_order_id) if oid)
    changes={"machine_state":{"old":LABELS.get(process,process),"new":LABELS.get(next_process,next_process)},
             "reason":{"old":None,"new":comment or (reason.name if reason else ACTIONS[action])}}
    def audit(entity_type,entity_id,entity_name):
        db.session.add(ChangeLog(entity_type=entity_type,entity_id=entity_id,entity_name=entity_name,
            action="update",category="production",changes=changes,user_id=user_id))
    audit("machine",machine_id,machine.machine_no)
    for oid in affected:
        order=db.session.get(Order,oid)
        audit("order",oid,order.order_no)
        if order.sampling:
            audit("sampling",order.sampling.id,order.order_no)
    db.session.flush()
    if commit: db.session.commit()
    return receipt,False
