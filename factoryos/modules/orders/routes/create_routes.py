from flask import render_template,request,redirect,url_for,flash,abort
from flask_login import login_required
from sqlalchemy.exc import IntegrityError,SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.access_control import valid_csrf
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.production.services.machine_control_service import acquire_control_lock
from factoryos.modules.orders.models import Order
from ..services.order_form_service import validate_form,form_context
from . import bp

@bp.route("/create",methods=["GET","POST"])
@login_required
def create():
    if request.method=="POST":
        if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
        if request.form.get("intent")=="preview":
            return render_template("orders/create.html",**form_context(form=request.form))
        try:
            acquire_control_lock()
            data=validate_form(request.form)
            order=Order(**data)
            db.session.add(order);db.session.flush()
            log_change("order",order.id,"create",entity_name=order.order_no,category="orders",
                changes={key:{"old":None,"new":data[key]} for key in ("article","article_name","tool_no","target_qty","cycle_time_s")})
            db.session.commit()
            flash("Auftrag mit Artikelstammdaten und Werkzeug erstellt.","success")
            return redirect(url_for("orders.detail",order_id=order.id))
        except ValueError as exc:
            db.session.rollback();flash(str(exc),"danger");status=400
        except IntegrityError:
            db.session.rollback();flash("Auftragsnummer ist bereits vergeben. Bitte prüfen.","danger");status=400
        except SQLAlchemyError:
            db.session.rollback();flash("Auftrag konnte nicht gespeichert werden. Bitte neu laden und erneut prüfen.","danger");status=409
        return render_template("orders/create.html",**form_context(form=request.form)),status
    return render_template("orders/create.html",**form_context(prefill=request.args.get("article","")))
