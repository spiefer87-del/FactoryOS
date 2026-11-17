"""Persisted queues and read-only forecasts, never automatic machine starts."""
import json
from datetime import datetime,timedelta
from math import ceil,isfinite
from types import SimpleNamespace
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.models.change_log import ChangeLog
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.production.models import (ProductionPlanEntry,ProductionPlanningState,
    MachinePlanningSettings,TimeBooking,MachineControlState,ProductionCalendarSettings)
from factoryos.modules.production.models import MachineToolState
from .tool_mount_service import tool_snapshot,tool_label
from .machine_control_service import acquire_control_lock,ControlConflict,ControlDenied,TERMINAL,LABELS
from .order_statistics import order_statistics,positive,count,local_label
from .calendar_service import get_calendar_exceptions,calculate_production_finish

PREVIEW_LIMIT=timedelta(days=366)

def planning_version():
    state=db.session.get(ProductionPlanningState,1)
    return state.version if state else 0

def queue(machine_id):
    return ProductionPlanEntry.query.filter_by(machine_id=machine_id,state="queued").order_by(ProductionPlanEntry.position,ProductionPlanEntry.id).all()

def audit(user_id,machine_id,old,new):
    machine=db.session.get(Machine,machine_id)
    db.session.add(ChangeLog(entity_type="machine",entity_id=machine_id,entity_name=machine.machine_no,
        user_id=user_id,category="planning",action="update",changes={"planning":{"old":old,"new":new}}))

def bump():
    state=db.session.get(ProductionPlanningState,1)
    if not state:state=ProductionPlanningState(id=1,version=0);db.session.add(state)
    state.version+=1

def _machine(machine_id,require_active=True):
    machine=db.session.get(Machine,machine_id)
    if not machine or (require_active and machine.machine_status!="aktiv"):raise ValueError("Bitte eine aktive Maschine auswählen.")
    return machine

def _order(order_id,machine_id):
    order=db.session.get(Order,order_id)
    if not order or order.is_project or (order.status or "").lower() in TERMINAL:
        raise ValueError("Nur offene Fertigungs- oder freigegebene Musterungsaufträge einplanen.")
    if order.sampling and (order.sampling.state not in ("in_progress","review") or order.sampling.machine_id!=machine_id):
        raise ValueError("Musterung muss in Bearbeitung/Prüfung und dieser Maschine zugeordnet sein.")
    if not positive(order.cycle_time_s) or not count(order.target_qty):
        raise ValueError("Soll-Zykluszeit und positive Sollmenge müssen am Auftrag hinterlegt sein.")
    return order

def _not_active(order_id):
    if (TimeBooking.query.filter(TimeBooking.end_time.is_(None),or_(TimeBooking.order_id==order_id,TimeBooking.prev_order_id==order_id)).first() or
        MachineControlState.query.filter_by(resume_order_id=order_id).first()):
        raise ValueError("Auftrag ist bereits aktiv oder unterbrochen reserviert. Zuerst den Maschinenvorgang beenden.")

def _normalize(machine_id):
    for index,entry in enumerate(queue(machine_id),1):entry.position=index

def modify_plan(user_id,expected_version,action,machine_id,entry_id=None,*,order_id=None,
                target_machine_id=None,setup_minutes=0,not_before=None,note="",available_from=None,
                availability_note="",ordered_ids=None,now=None):
    user=db.session.get(User,user_id)
    if not has_permission(user,"production.plan"):raise ControlDenied("Keine Berechtigung zur Auftragsplanung.")
    acquire_control_lock()
    if not has_permission(user,"production.plan"):raise ControlDenied("Planungsrecht wurde inzwischen geändert.")
    if str(planning_version())!=str(expected_version):raise ControlConflict("Plan wurde inzwischen geändert. Bitte neu laden und erneut entscheiden.")
    machine=_machine(machine_id,action in ("add","availability"))
    if len(note or "")>255 or len(availability_note or "")>255:raise ValueError("Notizen dürfen höchstens 255 Zeichen enthalten.")
    old=" → ".join(e.order.order_no for e in queue(machine_id)) or "Leere Reihenfolge"
    if action=="availability":
        if available_from and available_from<=(now if now is not None else datetime.utcnow()):
            raise ValueError("Die neue Verfügbarkeitsschätzung muss in der Zukunft liegen. Der angegebene Termin ist bereits erreicht oder überschritten.")
        if available_from and len((availability_note or "").strip())<5:
            raise ValueError("Manuelle Verfügbarkeit bitte begründen (mindestens 5 Zeichen).")
        settings=db.session.get(MachinePlanningSettings,machine_id)
        if not settings:settings=MachinePlanningSettings(machine_id=machine_id);db.session.add(settings)
        old=f"Verfügbarkeit: {local_label(settings.available_from)} · {settings.availability_note or ''}"
        settings.available_from=available_from;settings.availability_note=(availability_note or "").strip() or None
        new=f"Verfügbarkeit: {local_label(available_from)} · {settings.availability_note or ''}"
    elif action=="reorder":
        entries=queue(machine_id)
        if not isinstance(ordered_ids,list) or len(ordered_ids)!=len(entries) or set(ordered_ids)!={e.id for e in entries}:
            raise ValueError("Ungültige Reihenfolge. Bitte neu laden.")
        mapping={e.id:e for e in entries}
        for position,eid in enumerate(ordered_ids,1):mapping[eid].position=position;mapping[eid].updated_by_id=user_id
        new="Reihenfolge geändert"
    else:
        if action in ("add","update"):
            if not_before is not None:
                raise ValueError("Der Planbeginn wird aus der Maschinenverfügbarkeit und dem Ende des Vorgängers übernommen. Bitte die Seite neu laden und nur die zusätzliche Rüstzeit festlegen.")
            try:setup_minutes=int(setup_minutes)
            except (ValueError,TypeError):raise ValueError("Rüstzeit in ganzen Minuten angeben.")
            if not 0<=setup_minutes<=10080:raise ValueError("Rüstzeit muss zwischen 0 und 10080 Minuten liegen.")
        entry=db.session.get(ProductionPlanEntry,entry_id) if entry_id else None
        if action!="add" and (not entry or entry.machine_id!=machine_id or entry.state!="queued"):
            raise ControlConflict("Planeintrag nicht mehr in dieser Reihenfolge vorhanden.")
        if action=="add":
            order=_order(order_id,machine_id);_not_active(order.id)
            if ProductionPlanEntry.query.filter_by(order_id=order.id,state="queued").first():
                raise ControlConflict("Auftrag ist bereits eingeplant. Vorhandenen Eintrag verschieben statt doppelt anlegen.")
            entry=ProductionPlanEntry(machine_id=machine_id,order_id=order.id,position=len(queue(machine_id))+1,
                state="queued",created_by_id=user_id,updated_by_id=user_id,setup_minutes=setup_minutes,
                not_before=None,note=(note or "").strip() or None)
            db.session.add(entry);new=f"{order.order_no} angehängt · Rüsten {setup_minutes} Min · Beginn automatisch aus der Maschinenreihenfolge · {note}"
        elif action=="update":
            previous=f"Rüsten {entry.setup_minutes} Min"+(f" · bisheriger separater Planbeginn {local_label(entry.not_before)}" if entry.not_before else "")+f" · {entry.note or ''}"
            entry.setup_minutes=setup_minutes;entry.not_before=None;entry.note=(note or "").strip() or None
            new=f"{entry.order.order_no}: {previous} → Rüsten {setup_minutes} Min · Beginn automatisch aus der Maschinenreihenfolge · {note}"
        elif action in ("up","down"):
            entries=queue(machine_id);index=next(i for i,e in enumerate(entries) if e.id==entry.id)
            target=index+(-1 if action=="up" else 1)
            if target<0 or target>=len(entries):raise ValueError("Eintrag ist bereits am Ende dieser Richtung.")
            entries[index],entries[target]=entries[target],entries[index]
            for position,item in enumerate(entries,1):item.position=position;item.updated_by_id=user_id
            new=f"{entry.order.order_no} verschoben"
        elif action=="remove":
            entry.state="cancelled";new=f"{entry.order.order_no} aus Planung genommen (kein Auftrag gelöscht)"
        elif action=="transfer":
            if target_machine_id==machine_id:raise ValueError("Bitte eine andere Zielmaschine auswählen.")
            destination=_machine(target_machine_id);_order(entry.order_id,destination.id);_not_active(entry.order_id)
            entry.machine_id=destination.id;entry.position=len(queue(destination.id))+1
            new=f"{entry.order.order_no} nach {destination.machine_no} verschoben"
            audit(user_id,destination.id,"Reihenfolge",f"{entry.order.order_no} von {machine.machine_no} angehängt")
        else:raise ValueError("Unbekannter Planungsbefehl.")
        if entry:entry.updated_by_id=user_id
    db.session.flush();_normalize(machine_id)
    if action=="transfer":_normalize(target_machine_id)
    bump();db.session.flush()
    resulting=" → ".join(e.order.order_no for e in queue(machine_id)) or "Leere Reihenfolge"
    audit(user_id,machine_id,old,f"{new} · {resulting}")
    db.session.commit()

def assert_start_allowed(machine_id,order):
    assigned=ProductionPlanEntry.query.filter_by(order_id=order.id,state="queued").first()
    if assigned and assigned.machine_id!=machine_id:
        raise ControlConflict("Auftrag ist auf einer anderen Maschine eingeplant. Fertigungsleitung muss ihn zuerst umplanen.")
    first=ProductionPlanEntry.query.filter_by(machine_id=machine_id,state="queued").order_by(ProductionPlanEntry.position,ProductionPlanEntry.id).first()
    if first and first.order_id!=order.id:
        raise ControlConflict("Ein anderer Auftrag steht zuerst in der Maschinenplanung. Reihenfolge durch Fertigungsleitung ändern lassen.")

def consume_on_start(machine_id,order_id,booking,user_id):
    entry=ProductionPlanEntry.query.filter_by(machine_id=machine_id,order_id=order_id,state="queued").first()
    if entry:
        entry.state="started";entry.started_booking_id=booking.id;entry.updated_by_id=user_id
        db.session.flush();_normalize(machine_id);bump()
        audit(user_id,machine_id,f"{entry.order.order_no} eingeplant",f"Manuell gestartet · Buchung #{booking.id}")

def _working_start(cursor,settings,exceptions):
    return calculate_production_finish(cursor,0.000001,settings,exceptions)-timedelta(microseconds=1)

def build_schedule(now=None,settings=None,exceptions=None):
    now=now or datetime.utcnow()
    # Capture before reading rows. A concurrent commit then leaves an OLD form
    # revision, never a new revision attached to stale queue contents.
    version=planning_version()
    settings=settings or ProductionCalendarSettings.query.first() or SimpleNamespace(
        week_start_day=0,week_start_time="04:30",week_end_day=5,week_end_time="06:00")
    exceptions=get_calendar_exceptions() if exceptions is None else exceptions
    machines=Machine.query.order_by(Machine.machine_no).all()
    entries=ProductionPlanEntry.query.options(joinedload(ProductionPlanEntry.order),joinedload(ProductionPlanEntry.machine)).filter_by(state="queued").order_by(ProductionPlanEntry.position,ProductionPlanEntry.id).all()
    by_machine={};active_by={};stats_cache={};scheduled=[];result=[]
    for e in entries:by_machine.setdefault(e.machine_id,[]).append(e)
    for b in TimeBooking.query.filter(TimeBooking.machine_id.isnot(None),TimeBooking.end_time.is_(None)).all():
        active_by.setdefault(b.machine_id,[]).append(b)
    availability={s.machine_id:s for s in MachinePlanningSettings.query.all()}
    mounted=MachineToolState.query.filter_by(status='mounted').all()
    for machine in machines:
        current=active_by.get(machine.id,[]);manual=availability.get(machine.id)
        cursor=now;block=None;warnings=[];start_source="Maschinenverfügbarkeit ab jetzt";availability_expired=False;availability_needs_update=False
        if machine.machine_status!="aktiv":block="Maschine ist nicht aktiv."
        elif len(current)>1:block="Mehrere aktive Altbuchungen. Zuerst fachlich klären."
        elif current:
            active=current[0]
            if active.start_time>now:block="Aktive Buchung beginnt in der Zukunft. Zeitbasis prüfen."
            elif active.process in ("PROD","MUSTER") and active.order:
                stats=order_statistics(active.order,now,settings,exceptions);stats_cache[active.order_id]=stats
                if stats["eta"] and stats["forecast"]["remaining_seconds"]>0:
                    cursor=stats["eta"];start_source=f"Endprognose von Auftrag {active.order.order_no}";warnings.append("Laufender Auftrag: Belegung bis aktueller Endprognose, keine Abschlussbestätigung.")
                else:block="Ende des laufenden Auftrags nicht belastbar. Verfügbarkeit mit Begründung schätzen."
            elif active.process!="FREI":block="Laufender Rüst-/Störungs-/Pausen-/Wartungsvorgang ohne bekanntes Ende."
        if manual and manual.available_from:
            availability_expired=manual.available_from<=now
            can_estimate=block and len(current)<=1 and machine.machine_status=="aktiv" and (not current or current[0].start_time<=now)
            if can_estimate:
                if not availability_expired:
                    block=None;cursor=manual.available_from;start_source="Verfügbarkeitsschätzung der Maschine"
                else:
                    availability_needs_update=True
                    ongoing=(f"Auftrag {current[0].order.order_no} läuft weiterhin" if current and current[0].order else
                        f"Der Vorgang {LABELS.get(current[0].process,current[0].process)} ist weiterhin aktiv" if current else "Das tatsächliche Ende ist noch unbekannt")
                    block=(f"Der bisher geschätzte Verfügbarkeitstermin {local_label(manual.available_from)} wurde erreicht oder überschritten. "
                        f"{ongoing}; es liegt kein belastbares Ende vor. Deshalb ist die Planung erneut rot markiert. Bitte einen neuen zukünftigen Termin mit Begründung schätzen.")
            elif manual.available_from>cursor:
                cursor=manual.available_from;start_source="Verfügbarkeitsschätzung der Maschine"
            if availability_expired:
                warnings.append(f"Frühere Verfügbarkeitsschätzung: {local_label(manual.available_from)} · {manual.availability_note or ''}. Dieser Termin ist überschritten und gilt nicht mehr als zukünftige Verfügbarkeit.")
            else:
                warnings.append(f"Manuelle Verfügbarkeitsannahme: {local_label(manual.available_from)} · {manual.availability_note or ''}")
        rows=[]
        for entry in by_machine.get(machine.id,[]):
            tool_no=entry.order.tool_no or (entry.order.sampling.tool.tool_no if entry.order.sampling and entry.order.sampling.tool else None)
            if not tool_no and entry.order.article:
                article=Article.query.options(joinedload(Article.tools)).filter_by(article_no=entry.order.article).first()
                if article and len(article.tools)==1:tool_no=article.tools[0].tool_no
            row=dict(entry=entry,start=None,end=None,setup_start=None,setup_end=None,error=block,warnings=[],tool_no=tool_no,start_source=start_source,inherited_ready_at=cursor if not block else None)
            present=next((s for s in mounted if s.machine_id==machine.id),None)
            if present and tool_no and present.tool_no!=tool_no:
                row['warnings'].append('Werkzeug '+present.tool_no+' noch montiert. Abrüsten und Werkzeugwechsel vor Start berücksichtigen; keine automatische Abrüstung.')
            order=entry.order
            if not block:
                try:
                    _order(order.id,machine.id)
                    others=[b for group in active_by.values() for b in group if order.id in (b.order_id,b.prev_order_id) and b.machine_id!=machine.id]
                    if others:raise ValueError("Auftrag ist auf einer anderen Maschine aktiv.")
                    if order.id not in stats_cache:stats_cache[order.id]=order_statistics(order,now,settings,exceptions)
                    stats=stats_cache[order.id];forecast=stats["forecast"]
                    if not forecast or stats["remaining"]<=0:raise ValueError("Keine offene Restmenge oder keine berechenbare Laufzeit. Auftrag prüfen.")
                    seconds=ceil(stats["remaining"]/forecast["parts_per_cycle"])*float(order.cycle_time_s)
                    if not isfinite(seconds) or seconds<=0:raise ValueError("Ungültige Soll-Laufzeit.")
                    row.update(seconds=seconds,remaining=stats["remaining"],cavities=forecast["parts_per_cycle"],cycle=float(order.cycle_time_s))
                    if forecast["cavities_assumed"]:row["warnings"].append("Kavitäten fehlen: vorläufige Annahme 1 Teil/Zyklus.")
                    if not tool_no:row["warnings"].append("Kein eindeutiges Werkzeug: Werkzeugkonflikte können nicht vollständig geprüft werden.")
                    # One chain: availability / predecessor, setup, then production.
                    # Legacy not_before values remain stored until the next edit,
                    # but no longer delay queued orders independently.
                    row["setup_start"]=_working_start(cursor,settings,exceptions)
                    setup_seconds=entry.setup_minutes*60
                    if current and current[0].process=="RUEST" and current[0].order_id==order.id:
                        setup_seconds=0;row["warnings"].append("Rüsten bereits aktiv: angenommene Verfügbarkeit enthält das restliche Rüsten.")
                    elif not setup_seconds:row["warnings"].append("Keine zusätzliche Rüstzeit eingeplant (0 Minuten).")
                    row["setup_end"]=calculate_production_finish(row["setup_start"],setup_seconds,settings,exceptions)
                    row["start"]=_working_start(row["setup_end"],settings,exceptions)
                    row["end"]=calculate_production_finish(row["start"],seconds,settings,exceptions)
                    if row["end"]>now+PREVIEW_LIMIT:raise ValueError("Planende liegt mehr als 366 Tage voraus. Mengen/Zyklus und Verfügbarkeit prüfen.")
                    cursor=row["end"];start_source=f"Ende von Auftrag {order.order_no}";scheduled.append(row)
                except (ValueError,RuntimeError,OverflowError) as exc:
                    block=str(exc);row.update(start=None,end=None,setup_start=None,setup_end=None,error=block)
            rows.append(row)
        result.append(dict(machine=machine,rows=rows,current=current[0] if len(current)==1 else None,
            warnings=warnings,error=block,availability=manual,availability_expired=availability_expired,availability_needs_update=availability_needs_update,
            queue_ready_at=cursor if not block else None,queue_start_source=start_source,
            tool_mount_label=tool_label(tool_snapshot(machine.id))))
    # Cross-machine tool occupation is a warning, never silently auto-resolved.
    for i,row in enumerate(scheduled):
        if not row["tool_no"]:continue
        for mount in mounted:
            if mount.machine_id!=row['entry'].machine_id and mount.tool_no==row['tool_no']:
                row['warnings'].append('Werkzeug '+mount.tool_no+' weiterhin auf '+mount.machine.machine_no+' montiert – auch ohne Produktion. Abrüstende dort noch nicht bestätigt.')
        for mid,active_list in active_by.items():
            if mid==row["entry"].machine_id:continue
            for active in active_list:
                if active.process=="FREI" or (active.tool_no or (active.order.tool_no if active.order else None))!=row["tool_no"]:continue
                stats=stats_cache.get(active.order_id)
                end=stats["eta"] if stats and active.process in ("PROD","MUSTER") else None
                if end is None or row["setup_start"]<end:
                    row["warnings"].append(f"Werkzeug {row['tool_no']} aktuell auf {active.machine.machine_no if active.machine else mid} belegt; {'Ende unbekannt' if end is None else 'Überschneidung mit Endprognose'}.")
        for other in scheduled[i+1:]:
            if (row["entry"].machine_id!=other["entry"].machine_id and row["tool_no"]==other["tool_no"] and
                row["setup_start"]<other["end"] and other["setup_start"]<row["end"]):
                row["warnings"].append(f"Werkzeug {row['tool_no']} zeitgleich auf {other['entry'].machine.machine_no} eingeplant.")
                other["warnings"].append(f"Werkzeug {row['tool_no']} zeitgleich auf {row['entry'].machine.machine_no} eingeplant.")
    return dict(machines=result,version=version,now=now)
