from uuid import uuid4
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required, has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import DowntimeReason, MachineControlCommand
from factoryos.modules.production.services.machine_control_service import (
    execute, snapshot, current_booking, available_actions, ACTIONS, LABELS, PERMISSIONS,
    TERMINAL, ControlConflict, ControlDenied,
)
from factoryos.modules.production.services.order_statistics import local_label
from . import bp


@bp.route("/machine/<int:machine_id>/control",methods=["GET","POST"])
@login_required
@permission_required("production.view")
def machine_control(machine_id):
    machine=Machine.query.get_or_404(machine_id)
    embedded=request.args.get("embedded")=="1"
    error=None;status=200
    if request.method=="POST":
        if not valid_csrf(): abort(400,"Formular abgelaufen. Bitte neu laden.")
        try:
            _,replayed=execute(machine_id,current_user.id,request.form.get("action"),
                request.form.get("command_id"),request.form.get("revision"),
                order_id=request.form.get("order_id"),tool_no=request.form.get("tool_no"),
                reason_id=request.form.get("reason_id"),comment=request.form.get("comment",""))
            flash("Befehl war bereits verarbeitet – keine Doppelbuchung." if replayed else "Maschinenzustand gespeichert.","success")
            return redirect(url_for("production.machine_control",machine_id=machine_id,
                embedded="1" if embedded else None,changed="1"),code=303)
        except ControlDenied as exc:
            db.session.rollback();abort(403,str(exc))
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:
            db.session.rollback();error="Maschine wurde parallel geändert oder Datenbank ist belegt. Bitte neu laden und prüfen.";status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    process=active.process if active else "FREI"
    conflict=len(state["active"])>1
    actions=available_actions(process)
    permitted={action:has_permission(current_user,PERMISSIONS[action]) for action in ACTIONS}
    resume=state["resume_process"]
    if resume in ("RUEST","ABRUEST"): permitted["resume"] &= has_permission(current_user,"production.setup")
    elif resume=="WARTUNG": permitted["resume"] &= has_permission(current_user,"production.maintenance")
    elif resume=="SONSTIG": permitted["resume"] &= has_permission(current_user,"production.events")
    else: permitted["resume"] &= has_permission(current_user,"production.start")
    orders=Order.query.filter_by(is_project=False).order_by(Order.order_no).all()
    orders=[o for o in orders if (o.status or "").lower() not in TERMINAL and
            (not o.sampling or (o.sampling.state in ("in_progress","review") and o.sampling.machine_id==machine_id))]
    response=render_template("production/control/panel.html",machine=machine,state=state,active=active,
        process=process,actions=actions,action_labels=ACTIONS,labels=LABELS,permitted=permitted,
        conflict=conflict,error=error,orders=orders,
        tools=Tool.query.order_by(Tool.tool_no).all(),
        reasons=DowntimeReason.query.filter_by(active=True).order_by(DowntimeReason.name).all(),
        history=MachineControlCommand.query.filter_by(machine_id=machine_id).order_by(MachineControlCommand.id.desc()).limit(30).all(),
        embedded=embedded,command_id=str(uuid4()),local_label=local_label,
        selected_order=request.form.get("order_id",request.args.get("order_id","")),
        selected_tool=request.form.get("tool_no",""),selected_reason=request.form.get("reason_id",""),
        comment=request.form.get("comment", ""))
    return response,status,{"Cache-Control":"no-store","X-Frame-Options":"SAMEORIGIN"}


@bp.route("/machine/<int:machine_id>/control/state")
@login_required
@permission_required("production.view")
def machine_control_state(machine_id):
    Machine.query.get_or_404(machine_id)
    state=snapshot(machine_id)
    return jsonify(revision=state["revision"]),200,{"Cache-Control":"no-store"}
