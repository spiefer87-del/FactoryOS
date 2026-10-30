import secrets
from datetime import date, datetime
from flask import Blueprint, render_template, request, session, abort, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from factoryos.extensions import db
from factoryos.core.services.change_log_service import log_change
from factoryos.core.queries.change_log_queries import get_logs
from ..models import SamplingOrder
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.machine_service import start_machine_free
from ..definitions import *
from ..service import choices, save_sampling, completion_errors, complete_sampling

bp = Blueprint("sampling", __name__, url_prefix="/orders/sampling")


def csrf_token():
    if "sampling_csrf" not in session:
        session["sampling_csrf"] = secrets.token_urlsafe(32)
    return session["sampling_csrf"]


@bp.route("/<int:sampling_id>/pdf")
@login_required
def export_pdf(sampling_id):
    from ..pdf_service import build_pdf
    record = SamplingOrder.query.get_or_404(sampling_id)
    filename = f"Musterung_{record.id}_{secure_filename(record.order.order_no) or 'Auftrag'}.pdf"
    response = send_file(build_pdf(record), mimetype="application/pdf",
                         as_attachment=True, download_name=filename, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.route("/<int:sampling_id>/print")
@login_required
def print_order(sampling_id):
    from ..document_service import document_data
    record = SamplingOrder.query.get_or_404(sampling_id)
    response = render_template("sampling/print.html", record=record, document=document_data(record))
    return response, 200, {"Cache-Control": "private, no-store"}


def verify_csrf():
    expected = session.get("sampling_csrf", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected, supplied):
        abort(400, "Formular abgelaufen. Bitte Seite neu laden.")


@bp.route("/<int:sampling_id>/stop-booking", methods=["POST"])
@login_required
def stop_booking(sampling_id):
    verify_csrf()
    record = SamplingOrder.query.get_or_404(sampling_id)
    if record.state == "completed":
        abort(400, "Bereits abgeschlossen.")
    bookings = TimeBooking.query.filter_by(order_id=record.order_id, end_time=None).all()
    machine_ids = {b.machine_id for b in bookings if b.machine_id is not None}
    for booking in bookings:
        booking.end_time = datetime.utcnow()
    db.session.flush()
    for machine_id in machine_ids:
        if not TimeBooking.query.filter_by(machine_id=machine_id, end_time=None).first():
            start_machine_free(machine_id, current_user.id)
    if bookings:
        record.state = "review"
        log_change("sampling", record.id, "update", category="orders",
                   entity_name=record.order.order_no,
                   changes={"booking": {"old": "aktiv", "new": "beendet"}})
    db.session.commit()
    flash("Musterungsbuchung beendet. Durchführung und Prüfergebnisse bitte ergänzen.", "success")
    return redirect(url_for("sampling.detail", sampling_id=record.id))


def context():
    return dict(reasons=REASONS, states=STATES, check_labels=CHECKS,
                check_statuses=CHECK_STATUSES, text_fields=TEXT_FIELDS,
                number_fields=NUMBER_FIELDS, date_fields=DATE_FIELDS,
                yes_no_fields=YES_NO_FIELDS, initial_required=INITIAL_REQUIRED,
                csrf_token=csrf_token())


@bp.route("/")
@login_required
def overview():
    query = SamplingOrder.query
    reason = request.args.get("reason", "")
    state = request.args.get("state", "")
    if reason in REASONS:
        query = query.filter_by(reason=reason)
    if state in STATES:
        query = query.filter_by(state=state)
    return render_template("sampling/list.html", records=query.order_by(SamplingOrder.id.desc()).all(),
                           reason_filter=reason, state_filter=state, **context())


def edit_form(sampling=None):
    if request.method == "POST":
        verify_csrf()
        try:
            saved = save_sampling(request.form, current_user.id, sampling)
            flash("Musterungsauftrag gespeichert.", "success")
            return redirect(url_for("sampling.detail", sampling_id=saved.id))
        except (ValueError, IntegrityError, StaleDataError) as exc:
            db.session.rollback()
            message = str(exc) if isinstance(exc, ValueError) else "Auftrag wurde parallel geändert oder die Nummer ist bereits vergeben. Bitte neu laden."
            flash(message, "danger")
            return render_form(sampling, request.form), 400
    return render_form(sampling)


def render_form(sampling, submitted=None):
    values = {}
    if sampling:
        values.update(sampling.data or {})
        values.update(order_no=sampling.order.order_no, target_qty=sampling.order.target_qty,
                      reason=sampling.reason, state=sampling.state, version=sampling.version)
        for key in ("article_id", "customer_id", "tool_id", "material_id", "machine_id", "previous_id"):
            values[key] = str(getattr(sampling, key) or "")
        for check in sampling.checks:
            values["check_" + check.key] = check.status
            values["note_" + check.key] = check.note or ""
            values["date_" + check.key] = check.evidence_date.isoformat() if check.evidence_date else ""
    else:
        values.update(target_qty=1, state="draft", reason=request.args.get("reason", ""),
                      previous_id=request.args.get("previous_id", ""))
    if submitted:
        values.update(submitted)
    return render_template("sampling/form.html", record=sampling, values=values,
                           **choices(), **context())


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    return edit_form()


@bp.route("/<int:sampling_id>")
@login_required
def detail(sampling_id):
    record = SamplingOrder.query.get_or_404(sampling_id)
    return render_template("sampling/detail.html", record=record,
                           active_bookings=TimeBooking.query.filter_by(order_id=record.order_id, end_time=None).all(),
                           errors=completion_errors(record) if record.state != "completed" else [],
                           logs=get_logs(entity_type="sampling", entity_id=record.id, limit=25),
                           **context())


@bp.route("/<int:sampling_id>/edit", methods=["GET", "POST"])
@login_required
def edit(sampling_id):
    record = SamplingOrder.query.get_or_404(sampling_id)
    if record.state == "completed":
        flash("Abgeschlossene Musterungen sind schreibgeschützt.", "warning")
        return redirect(url_for("sampling.detail", sampling_id=record.id))
    return edit_form(record)


@bp.route("/<int:sampling_id>/complete", methods=["POST"])
@login_required
def complete(sampling_id):
    verify_csrf()
    record = SamplingOrder.query.get_or_404(sampling_id)
    try:
        if str(record.version) != request.form.get("version"):
            raise ValueError("Auftrag wurde geändert. Bitte neu laden.")
        complete_sampling(record, current_user.id)
        flash("Musterung erfolgreich abgeschlossen.", "success")
    except (ValueError, StaleDataError) as exc:
        db.session.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else "Auftrag wurde parallel geändert. Bitte neu laden.", "danger")
    return redirect(url_for("sampling.detail", sampling_id=record.id))


@bp.route("/<int:sampling_id>/external", methods=["POST"])
@login_required
def external_followup(sampling_id):
    verify_csrf()
    record = SamplingOrder.query.get_or_404(sampling_id)
    try:
        if record.state != "completed" or record.reason == "initial":
            raise ValueError("Externe Nachverfolgung ist nur nach intern abgeschlossenen Folgemusterungen möglich.")
        if str(record.version) != request.form.get("version"):
            raise ValueError("Auftrag wurde geändert. Bitte neu laden.")
        check = next(c for c in record.checks if c.key == "external")
        status = request.form.get("external_status")
        note = request.form.get("external_note", "").strip()
        if status not in ("open", "granted", "rejected", "not_required"):
            raise ValueError("Ungültiger Freigabestatus.")
        if len(note) > 5000 or (status in ("rejected", "not_required") and not note):
            raise ValueError("Bitte eine gültige Begründung angeben (maximal 5000 Zeichen).")
        raw_date = request.form.get("external_date", "")
        try:
            evidence_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError:
            raise ValueError("Ungültiges Datum.")
        if status in ("granted", "rejected") and evidence_date is None:
            raise ValueError("Für die Kundenentscheidung ist ein Datum erforderlich.")
        before = {"status": check.status, "note": check.note, "date": str(check.evidence_date or "")}
        check.status, check.note, check.evidence_date = status, note, evidence_date
        check.updated_by_id, check.updated_at = current_user.id, datetime.utcnow()
        record.version += 1
        log_change("sampling", record.id, "update", category="orders",
                   entity_name=record.order.order_no, changes={"external": {"old": before,
                       "new": {"status": status, "note": note, "date": str(evidence_date or "")}}})
        db.session.commit()
        flash("Kundenfreigabe separat aktualisiert. Der interne Abschluss bleibt erhalten.", "success")
    except (ValueError, StaleDataError) as exc:
        db.session.rollback()
        flash(str(exc) if isinstance(exc, ValueError) else "Auftrag wurde parallel geändert.", "danger")
    return redirect(url_for("sampling.detail", sampling_id=record.id))

