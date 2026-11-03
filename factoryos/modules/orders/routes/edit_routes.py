from flask import render_template,request,redirect,url_for,flash,abort
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.access_control import valid_csrf
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,MachineControlState,ProductionPlanEntry
from factoryos.modules.production.services.machine_control_service import acquire_control_lock,TERMINAL
from ..services.order_form_service import validate_form,form_context
from . import bp

@bp.route("/edit/<int:order_id>",methods=["GET","POST"])
@login_required
def edit(order_id):
    order=Order.query.get_or_404(order_id)
    if order.sampling:return redirect(url_for("sampling.detail",sampling_id=order.sampling.id))
    if request.method=="POST":
        if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
        if request.form.get("intent")=="preview":
            return render_template("orders/edit.html",**form_context(order,request.form))
        try:
            acquire_control_lock()
            data=validate_form(request.form,order)
            occupied=(TimeBooking.query.filter(TimeBooking.end_time.is_(None),or_(TimeBooking.order_id==order.id,TimeBooking.prev_order_id==order.id)).first() or
                MachineControlState.query.filter_by(resume_order_id=order.id).first() or
                ProductionPlanEntry.query.filter_by(order_id=order.id,state="queued").first())
            if occupied and (data.get("article",order.article)!=order.article or data.get("tool_no",order.tool_no)!=order.tool_no or str(data.get("status",order.status) or "").lower() in TERMINAL):
                raise ValueError("Auftrag ist aktiv, reserviert oder eingeplant. Vor Artikel-/Werkzeugwechsel oder Abschluss zuerst Maschinenvorgang beenden und gegebenenfalls aus der Planung nehmen.")
            changes={}
            for key,value in data.items():
                old=getattr(order,key)
                if old!=value:changes[key]={"old":old,"new":value}
                setattr(order,key,value)
            if changes:log_change("order",order.id,"update",entity_name=order.order_no,category="orders",changes=changes)
            db.session.commit();flash("Auftrag gespeichert. Artikelname wurde aus den Stammdaten übernommen.","success")
            return redirect(url_for("orders.detail",order_id=order.id))
        except ValueError as exc:
            db.session.rollback();flash(str(exc),"danger");status=400
        except SQLAlchemyError:
            db.session.rollback();flash("Auftrag wurde parallel geändert oder konnte nicht gespeichert werden. Bitte neu laden.","danger");status=409
        return render_template("orders/edit.html",**form_context(order,request.form)),status
    return render_template("orders/edit.html",**form_context(order))
