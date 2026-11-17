"""One atomic, idempotent completion path for office and machine touch panels."""
import hashlib
import json
import re
from datetime import datetime
from uuid import UUID
from sqlalchemy import func,or_
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.models.change_log import ChangeLog
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from ..models import (OrderCompletion,QuantityReport,TimeBooking,MachineControlState,
    MachineControlCommand,ProductionPlanEntry,ProductionPlanningState)
from .machine_control_service import acquire_control_lock,snapshot,ControlConflict,ControlDenied,TERMINAL


def completion_context(order):
    good,scrap,count,last=db.session.query(func.coalesce(func.sum(QuantityReport.good_qty),0),
        func.coalesce(func.sum(QuantityReport.scrap_qty),0),func.count(QuantityReport.id),
        func.max(QuantityReport.id)).filter_by(order_id=order.id).one()
    bookings=TimeBooking.query.filter(TimeBooking.end_time.is_(None),
        or_(TimeBooking.order_id==order.id,TimeBooking.prev_order_id==order.id)).order_by(TimeBooking.id).all()
    states=MachineControlState.query.filter_by(resume_order_id=order.id).order_by(MachineControlState.machine_id).all()
    machines={b.machine_id for b in bookings}|{s.machine_id for s in states}
    plans=ProductionPlanEntry.query.filter_by(order_id=order.id).order_by(ProductionPlanEntry.id).all()
    value=dict(order=order.id,status=order.status,updated=str(order.updated_at),target=order.target_qty,
        good=int(good),scrap=int(scrap),count=count,last=last,
        machines={str(mid):snapshot(mid) for mid in machines if mid},
        bookings=[b.id for b in bookings],plans=[(p.id,p.state,p.machine_id,p.position) for p in plans])
    revision=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return dict(good=int(good),scrap=int(scrap),revision=revision,bookings=bookings,states=states,
                machines=machines,plans=plans)


def _quantity(raw,label):
    if isinstance(raw,bool) or not re.fullmatch(r"[0-9]{1,10}",str(raw).strip() if raw is not None else ''):
        raise ValueError(label+": bitte eine nicht negative ganze Gesamtstückzahl eingeben.")
    value=int(raw)
    if value>2147483647:raise ValueError(label+": Stückzahl ist zu groß.")
    return value


def complete_order(order_id,user_id,command_id,revision,*,good_qty,scrap_qty,reason="",
                   confirmed=False,short_confirmed=False,source="office",machine_id=None):
    permission={"office":"orders.complete","machine":"production.complete_order"}.get(source)
    user=db.session.get(User,user_id)
    if not permission or not has_permission(user,permission):raise ControlDenied("Keine Berechtigung zum Auftragsabschluss.")
    try:
        if str(UUID(command_id))!=command_id:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ValueError("Ungültige Abschlusskennung. Bitte neu laden.")
    good=_quantity(good_qty,"Gutmenge");scrap=_quantity(scrap_qty,"Ausschussmenge")
    reason=(reason or "").strip()
    if len(reason)>255:raise ValueError("Begründung: maximal 255 Zeichen.")
    if not confirmed:raise ValueError("Bitte Endmengen und endgültigen Auftragsabschluss ausdrücklich bestätigen.")
    payload=dict(order_id=order_id,revision=revision,good=good,scrap=scrap,reason=reason,
        short_confirmed=bool(short_confirmed),source=source,machine_id=machine_id)
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    acquire_control_lock()
    user=db.session.get(User,user_id)
    if not has_permission(user,permission):raise ControlDenied("Berechtigung wurde inzwischen geändert.")
    previous=OrderCompletion.query.filter_by(command_id=command_id).first()
    if previous:
        if previous.user_id!=user_id or previous.payload_hash!=digest:raise ControlConflict("Abschlusskennung wurde bereits für einen anderen Inhalt verwendet.")
        db.session.commit();return previous,True
    order=db.session.get(Order,order_id)
    if not order:raise ValueError("Auftrag nicht gefunden.")
    if order.is_project:raise ValueError("Projektaufträge werden nicht als stückbezogener Fertigungsauftrag abgeschlossen.")
    if order.sampling:raise ValueError("Musterungsaufträge bitte im eigenen Prüf- und Freigabeablauf abschließen.")
    if OrderCompletion.query.filter_by(order_id=order.id).first() or (order.status or "").lower() in TERMINAL:
        raise ControlConflict("Auftrag ist bereits abgeschlossen, gesperrt oder storniert. Kein erneuter Abschluss.")
    context=completion_context(order)
    if not revision or context['revision']!=revision:raise ControlConflict("Auftrag, Mengen oder Maschinenstand wurden geändert. Bitte neu laden und Endmengen erneut prüfen.")
    if good<context['good'] or scrap<context['scrap']:
        raise ValueError("Endmengen dürfen bereits gebuchte Gut-/Ausschussmengen nicht unterschreiten. Bestehende Mengen fachlich korrigieren lassen.")
    from factoryos.modules.inventory.service import protect_final_total
    protect_final_total(order.id,good)
    target=order.target_qty or 0
    if target<=0 and len(reason)<5:raise ValueError('Sollstückzahl fehlt: manuellen Abschluss mit mindestens 5 Zeichen begründen.')
    if good<target and (not short_confirmed or len(reason)<5):
        raise ValueError("Gutmenge liegt unter der Sollstückzahl: Abweichung ausdrücklich bestätigen und mit mindestens 5 Zeichen begründen.")
    machines=context['machines']
    if None in machines or len(machines)>1 or len(context['bookings'])>1:
        raise ControlConflict("Mehrdeutige aktive Buchungen oder Reservierungen. Bitte vor dem Abschluss fachlich klären.")
    active=context['bookings'][0] if context['bookings'] else None
    mid=next(iter(machines),None)
    if source=='machine' and (not active or mid!=machine_id):raise ControlConflict("Dieser Auftrag läuft nicht mehr auf dieser Maschine. Bitte neu laden.")
    if context['states'] and not active:raise ControlConflict("Auftrag hat eine verwaiste Maschinenreservierung. Bitte zuerst klären.")
    state=None;before=None
    if active:
        if active.order_id!=order.id:raise ControlConflict('Aktive Buchung gehört nicht eindeutig zu diesem Auftrag.')
        before=snapshot(mid)
        if len(before['active'])!=1:raise ControlConflict("Maschine hat mehrere aktive Buchungen. Abschluss gesperrt.")
        state=db.session.get(MachineControlState,mid)
        if active.process not in ('PROD','PAUSE') or (state and state.resume_process not in (None,'PROD')):
            raise ControlConflict("Vor dem Abschluss bitte Störung, Rüsten, Wartung oder Musterung regulär beenden. Diese Zustände werden nicht automatisch quittiert.")
        if state and state.resume_order_id not in (None,order.id):raise ControlConflict("Maschinenreservierung gehört zu einem anderen Auftrag.")
    now=datetime.utcnow()
    if active and active.start_time>now:raise ControlConflict("Aktive Buchung liegt in der Zukunft. Zeitbasis zuerst klären.")
    completion=OrderCompletion(order_id=order.id,user_id=user_id,machine_id=mid,good_qty=good,scrap_qty=scrap,
        reported_good_qty=context['good'],reported_scrap_qty=context['scrap'],target_qty=target,
        previous_status=order.status or '',reason=reason or 'Sollstückzahl erreicht',source=source,
        command_id=command_id,payload_hash=digest,closed_at=now)
    db.session.add(completion);order.status='finished';order.updated_at=now
    if active:
        active.end_time=now
        from ..models import MachineToolState
        if not db.session.get(MachineToolState,mid):
            db.session.add(MachineToolState(machine_id=mid,status='unknown',tool_no=active.tool_no,
                requires_confirmation=False,updated_at=now,updated_by_id=user_id))
        if not state:state=MachineControlState(machine_id=mid,version=0);db.session.add(state)
        state.resume_process=None;state.resume_order_id=None;state.resume_tool_no=None;state.version+=1
        db.session.add(TimeBooking(user_id=user_id,machine_id=mid,order_id=None,process='FREI',type='START',
            start_time=now,tool_no=active.tool_no,comment='Auftrag '+order.order_no+' abgeschlossen'))
    for plan in context['plans']:
        if plan.state in ('queued','started'):
            plan.state='completed';plan.updated_by_id=user_id;plan.updated_at=now
    planning=db.session.get(ProductionPlanningState,1)
    if planning:planning.version+=1
    db.session.flush()
    changes=dict(status={'old':completion.previous_status,'new':'finished'},
        final_good_qty={'old':context['good'],'new':good},final_scrap_qty={'old':context['scrap'],'new':scrap},
        completion_reason={'old':None,'new':completion.reason})
    db.session.add(ChangeLog(entity_type='order',entity_id=order.id,entity_name=order.order_no,action='update',
        category='order_completion',changes=changes,user_id=user_id))
    if active:
        after=snapshot(mid)
        before['completion_order_id']=order.id;after['completion']=dict(order_id=order.id,good_qty=good,scrap_qty=scrap,status='finished')
        db.session.add(MachineControlCommand(command_id=command_id,machine_id=mid,user_id=user_id,source='app',
            action='complete_order',payload_hash=digest,comment=completion.reason,before_state=before,after_state=after))
        db.session.add(ChangeLog(entity_type='machine',entity_id=mid,entity_name=active.machine.machine_no,
            action='update',category='order_completion',changes=changes,user_id=user_id))
    db.session.commit()
    return completion,False
