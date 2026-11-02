from flask import render_template, request, redirect, url_for, flash, abort, session
from hashlib import sha256
import json
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required
from factoryos.core.access_control import valid_csrf
from factoryos.modules.production.models import TimeBooking
from ..services.booking_time_service import eligible, revision, parse_local_start, correction_plan, apply_correction
from ..services.order_statistics import local_time, local_label
from . import bp

@bp.route("/booking/<int:booking_id>/start-time",methods=["GET","POST"])
@login_required
@permission_required("production.edit_booking_time")
def edit_booking_time(booking_id):
    booking=TimeBooking.query.get_or_404(booking_id)
    try: eligible(booking)
    except ValueError as error: abort(400,description=str(error))
    current=revision(booking)
    values={"start_time":local_time(booking.start_time).strftime("%Y-%m-%dT%H:%M:%S"),
            "reason":"","fold":"","revision":current}
    plan=None
    proposed=None
    status=200
    if request.method=="POST":
        if not valid_csrf(): abort(400,description="Sicherheitsprüfung fehlgeschlagen. Bitte neu laden.")
        values.update({key:request.form.get(key,"") for key in values})
        if values["revision"]!=current: abort(409,description="Buchungen wurden geändert. Bitte neu laden.")
        intent=request.form.get("intent")
        if intent not in ("preview","commit"): abort(400)
        try:
            proposed=parse_local_start(values["start_time"],values["fold"])
            plan=correction_plan(booking,proposed,values["reason"])
            digest=sha256(json.dumps({"booking":booking.id,**values},sort_keys=True).encode()).hexdigest()
            if intent=="commit":
                if session.get("booking_time_preview")!=digest:
                    raise ValueError("Bitte diese Änderung zuerst als Vorschau prüfen.")
                saved=apply_correction(booking,proposed,values["reason"],values["revision"])
                session.pop("booking_time_preview",None)
                flash("Startzeit korrigiert und mit Begründung protokolliert.","success")
                return redirect(url_for("orders.detail",order_id=saved.order_id))
            session["booking_time_preview"]=digest
        except ValueError as error:
            db.session.rollback();flash(str(error),"danger");status=400;plan=None
        except SQLAlchemyError:
            db.session.rollback();flash("Keine Änderung gespeichert. Buchungen wurden parallel geändert oder die Datenbank ist belegt.","danger");status=409;plan=None
    return render_template("production/booking/edit_start_time.html",booking=booking,values=values,
                           plan=plan,proposed=proposed,local_label=local_label),status
