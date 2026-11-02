import json
from flask import request,render_template,redirect,url_for,flash,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import ProductionPlanEntry,TimeBooking,MachineControlState
from factoryos.modules.production.services.planning_service import build_schedule,modify_plan
from factoryos.modules.production.services.machine_control_service import ControlConflict,ControlDenied,TERMINAL
from factoryos.modules.production.services.booking_time_service import parse_local_start
from factoryos.modules.production.services.order_statistics import local_label,local_time,duration
from . import bp

def optional_time(name):
    value=request.form.get(name,"").strip()
    if not value:return None
    result=parse_local_start(value,request.form.get(name+"_fold",""))
    if not 1970<=result.year<=2100:raise ValueError("Zeitvorgaben zwischen 1970 und 2100 wählen.")
    return result

def ident(name,optional=False):
    value=request.form.get(name,"")
    if optional and not value:return None
    if not value.isdecimal() or not 1<=int(value)<2**63:raise ValueError("Ungültige Auswahl. Bitte neu laden.")
    return int(value)

@bp.route("/planning",methods=["GET","POST"])
@login_required
@permission_required("production.view")
def planning():
    error=None;status=200
    if request.method=="POST":
        if not has_permission(current_user,"production.plan"):abort(403)
        if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
        try:
            ordered=json.loads(request.form.get("ordered_ids","null"))
            if ordered is not None and (not isinstance(ordered,list) or any(type(i)!=int for i in ordered)):
                raise ValueError("Ungültige Reihenfolge.")
            modify_plan(current_user.id,request.form.get("version"),request.form.get("action"),ident("machine_id"),
                ident("entry_id",True),order_id=ident("order_id",True),target_machine_id=ident("target_machine_id",True),
                setup_minutes=request.form.get("setup_minutes","0"),not_before=optional_time("not_before"),
                note=request.form.get("note",""),available_from=optional_time("available_from"),
                availability_note=request.form.get("availability_note",""),ordered_ids=ordered)
            flash("Auftragsplanung gespeichert. Es wurde keine Maschinenbuchung gestartet.","success")
            return redirect(url_for("production.planning",_anchor="plan-machine-"+request.form["machine_id"]),code=303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except (ValueError,TypeError) as exc:
            db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:
            db.session.rollback();error="Plan wurde parallel geändert oder Datenbank ist belegt. Bitte neu laden und prüfen.";status=409
    schedule=build_schedule()
    assigned={e.order_id for e in ProductionPlanEntry.query.filter_by(state="queued")}
    assigned.update(b.order_id for b in TimeBooking.query.filter_by(end_time=None) if b.order_id)
    assigned.update(b.prev_order_id for b in TimeBooking.query.filter_by(end_time=None) if b.prev_order_id)
    assigned.update(s.resume_order_id for s in MachineControlState.query.all() if s.resume_order_id)
    orders=[o for o in Order.query.order_by(Order.order_no).all() if not o.is_project and o.id not in assigned and
        (o.status or "").lower() not in TERMINAL and (not o.sampling or o.sampling.state in ("in_progress","review"))]
    return render_template("production/planning/board.html",schedule=schedule,orders=orders,
        can_plan=has_permission(current_user,"production.plan"),local_label=local_label,duration=duration,
        local_input=lambda value:local_time(value).strftime("%Y-%m-%dT%H:%M:%S") if value else "",
        local_fold=lambda value:str(local_time(value).fold) if value else "",
        error=error,history=ChangeLog.query.filter_by(category="planning").order_by(ChangeLog.id.desc()).limit(30).all()),status,{"Cache-Control":"no-store"}
