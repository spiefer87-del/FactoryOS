from datetime import date

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from factoryos.core.auth import role_required
from factoryos.modules.production.services.calendar_service import (
    WEEKDAYS,
    create_calendar_exception,
    delete_calendar_exception,
    get_calendar_exceptions,
    get_or_create_calendar_settings,
    update_calendar_settings,
)

from . import bp


@bp.route("/booking/setup", methods=["GET", "POST"])
@login_required
@role_required("admin")
def booking_calendar_setup():
    settings = get_or_create_calendar_settings(commit=True)

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save_weekly_schedule":
                update_calendar_settings(settings, request.form)
                flash("Regelmäßige Produktionszeiten wurden gespeichert.", "success")
            elif action == "add_exception":
                create_calendar_exception(request.form, current_user.id)
                flash("Produktionsfreie Ausnahme wurde hinzugefügt.", "success")
            else:
                flash("Unbekannte Kalenderaktion.", "danger")
        except ValueError as exc:
            flash(str(exc), "danger")
        return redirect(url_for("production.booking_calendar_setup"))

    return render_template(
        "production/booking/calendar_setup.html",
        settings=settings,
        weekdays=WEEKDAYS,
        exceptions=get_calendar_exceptions(),
        today=date.today(),
    )


@bp.route("/booking/setup/exceptions/<int:exception_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_booking_calendar_exception(exception_id):
    if delete_calendar_exception(exception_id):
        flash("Kalenderausnahme wurde gelöscht.", "success")
    else:
        flash("Kalenderausnahme wurde nicht gefunden.", "danger")
    return redirect(url_for("production.booking_calendar_setup"))
