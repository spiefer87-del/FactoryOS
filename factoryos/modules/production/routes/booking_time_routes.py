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
from markupsafe import Markup
from flask_login import current_user
from factoryos.core.auth import has_permission
from ..services.booking_time_service import BookingOverlapError
from ..services.booking_time_service import eligible_end, end_correction_plan, apply_end_correction

@bp.route("/booking/<int:booking_id>/start-time",methods=["GET","POST"])
@login_required
@permission_required("production.edit_booking_time")
def edit_booking_time(booking_id):
    return _edit_boundary(booking_id,'start')

@bp.route("/booking/<int:booking_id>/end-time",methods=["GET","POST"])
@login_required
@permission_required("production.edit_booking_time")
def edit_booking_end_time(booking_id):
    return _edit_boundary(booking_id,'end')

def _edit_boundary(booking_id,boundary):
    is_end=boundary=='end'
    field='end_time' if is_end else 'start_time'
    label='Endzeit' if is_end else 'Startzeit'
    preview_key='booking_end_time_preview' if is_end else 'booking_time_preview'
    validate=eligible_end if is_end else eligible
    make_plan=end_correction_plan if is_end else correction_plan
    save=apply_end_correction if is_end else apply_correction
    booking=TimeBooking.query.get_or_404(booking_id)
    try: validate(booking)
    except ValueError as error: abort(400,description=str(error))
    current=revision(booking)
    values={field:local_time(getattr(booking,field)).strftime("%Y-%m-%dT%H:%M:%S"),
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
            proposed=parse_local_start(values[field],values["fold"])
            plan=make_plan(booking,proposed,values["reason"])
            digest=sha256(json.dumps({"booking":booking.id,"boundary":boundary,**values},sort_keys=True).encode()).hexdigest()
            if intent=="commit":
                if session.get(preview_key)!=digest:
                    raise ValueError("Bitte diese Änderung zuerst als Vorschau prüfen.")
                saved=save(booking,proposed,values["reason"],values["revision"])
                session.pop(preview_key,None)
                flash(label+" korrigiert und mit Begründung protokolliert.","success")
                return redirect(url_for("orders.detail",order_id=saved.order_id))
            session[preview_key]=digest
        except ValueError as error:
            db.session.rollback()
            message=str(error)
            if isinstance(error,BookingOverlapError) and has_permission(current_user,'production.view'):
                message=Markup('{} <a href="{}">Buchung #{} prüfen / bearbeiten</a>').format(message,url_for('booking_review.detail',booking_id=error.booking_id),error.booking_id)
            flash(message,"danger");status=400;plan=None
        except SQLAlchemyError:
            db.session.rollback();flash("Keine Änderung gespeichert. Buchungen wurden parallel geändert oder die Datenbank ist belegt.","danger");status=409;plan=None
    return render_template("production/booking/edit_start_time.html",booking=booking,values=values,
                           plan=plan,proposed=proposed,local_label=local_label,
                           is_end=is_end,field=field,boundary_label=label),status
