from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required, has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.modules.orders.import_models import ERPImportBatch
from factoryos.modules.orders.services.erp_excel_reader import read_erp_excel, clean
from factoryos.modules.orders.services.erp_import_service import (
    ENTITIES, FIELD_LABELS, MATERIAL_TYPES, MACHINE_TYPES, default_choices,
    options, suggestions, build_plan, commit_plan,
)
from . import bp


def owned_batch(batch_id):
    batch = ERPImportBatch.query.filter_by(id=batch_id, user_id=current_user.id).first_or_404()
    if batch.created_at < datetime.utcnow() - timedelta(days=7):
        abort(410, description="Importentwurf ist abgelaufen. Bitte Datei erneut hochladen.")
    return batch


def require_csrf():
    if not valid_csrf(): abort(400, description="Sicherheitsprüfung fehlgeschlagen. Bitte Seite neu laden.")


def lock_batch(batch):
    try: version = int(request.form.get("version", ""))
    except ValueError: abort(400)
    changed = (ERPImportBatch.query.filter_by(id=batch.id, user_id=current_user.id, version=version)
               .update({ERPImportBatch.version: version + 1}, synchronize_session=False))
    if changed != 1:
        db.session.rollback()
        abort(409, description="Der Import wurde in einem anderen Fenster geändert. Bitte neu laden.")
    batch.version = version + 1


def row_plan(batch, index, row):
    plan = build_plan(row, current_user)
    number = row["fields"].get("order_no", "")
    if number and any(other["state"] != "skipped" and clean(other["fields"].get("order_no")) == number
                      for i, other in enumerate(batch.rows) if i != index):
        plan["errors"].append("Diese FA-Nummer kommt mehrfach im Import vor. Positionen werden nicht automatisch zusammengefasst. Doppelte Zeilen überspringen oder Nummern fachlich klären.")
    return plan


@bp.route("/import", methods=["GET", "POST"])
@login_required
@permission_required("orders.excel_import")
def import_orders():
    if request.method == "POST":
        require_csrf()
        file = request.files.get("file")
        if not file or not (file.filename or "").lower().endswith(".xlsx"):
            flash("Bitte eine XLSX-Datei auswählen.", "danger")
        else:
            try:
                sheet, rows = read_erp_excel(file, clean(request.form.get("sheet_name")))
                batch = ERPImportBatch(id=str(uuid4()), user_id=current_user.id,
                    filename=file.filename.replace("\\", "/").split("/")[-1][:255], sheet=sheet[:100], rows=rows)
                db.session.add(batch)
                db.session.commit()
                return redirect(url_for("orders.import_batch", batch_id=batch.id))
            except (ValueError, SQLAlchemyError) as error:
                db.session.rollback()
                flash(str(error) if isinstance(error, ValueError) else "Importentwurf konnte nicht gespeichert werden. Bitte Datenbankupgrade prüfen.", "danger")
    batches = (ERPImportBatch.query.filter_by(user_id=current_user.id)
               .filter(ERPImportBatch.created_at >= datetime.utcnow() - timedelta(days=7))
               .order_by(ERPImportBatch.created_at.desc()).limit(10).all())
    return render_template("orders/import_upload.html", batches=batches)


@bp.route("/import/<batch_id>")
@login_required
@permission_required("orders.excel_import")
def import_batch(batch_id):
    batch = owned_batch(batch_id)
    return render_template("orders/import_batch.html", batch=batch)


@bp.route("/import/<batch_id>/row/<int:index>", methods=["GET", "POST"])
@login_required
@permission_required("orders.excel_import")
def import_row(batch_id, index):
    batch = owned_batch(batch_id)
    if not 0 <= index < len(batch.rows): abort(404)
    row = default_choices(batch.rows[index], current_user)
    if row["state"] in ("imported", "skipped"):
        return redirect(url_for("orders.import_batch", batch_id=batch.id))
    if request.method == "POST":
        require_csrf()
        action = request.form.get("intent")
        if action not in ("preview", "commit", "skip"): abort(400)
        try:
            lock_batch(batch)
            rows = deepcopy(batch.rows)
            if action == "skip":
                row["state"] = "skipped"
            elif action == "preview":
                for key in FIELD_LABELS: row["fields"][key] = clean(request.form.get(key))
                row["fields"]["material_type"] = clean(request.form.get("material_type"))
                row["fields"]["machine_type"] = clean(request.form.get("machine_type"))
                row["choices"] = {kind: clean(request.form.get("choice_" + kind)) for kind in ENTITIES}
                row["acknowledged"] = request.form.get("acknowledged") == "yes"
                row["reviewed"] = True
                row["action"] = request.form.get("order_action", "create")
                if row["action"] not in ("create", "update"): abort(400)
                plan = row_plan(batch, index, row)
                row["state"] = "ready" if not plan["errors"] else "pending"
                row["fingerprint"] = plan["fingerprint"] if not plan["errors"] else ""
            else:
                stored = rows[index]
                if stored["state"] != "ready": abort(409, description="Zeile bitte zuerst prüfen.")
                row = stored
                plan = row_plan(batch, index, row)
                if plan["errors"] or plan["fingerprint"] != row.get("fingerprint"):
                    row["state"] = "pending"
                    row["fingerprint"] = ""
                    flash("Angaben, Rechte oder Stammdaten haben sich geändert. Bitte erneut prüfen.", "warning")
                else:
                    order = commit_plan(row, plan, batch, current_user)
                    row["state"] = "imported"
                    row["order_id"] = order.id
                    flash("Auftrag " + order.order_no + " erfolgreich übernommen.", "success")
            rows[index] = row
            batch.rows = rows
            db.session.commit()
            if row["state"] in ("imported", "skipped"):
                following = next((i for i, item in enumerate(rows) if item["state"] not in ("imported", "skipped")), None)
                if following is not None: return redirect(url_for("orders.import_row", batch_id=batch.id, index=following))
                return redirect(url_for("orders.import_batch", batch_id=batch.id))
            return redirect(url_for("orders.import_row", batch_id=batch.id, index=index))
        except SQLAlchemyError:
            db.session.rollback()
            flash("Nichts aus dieser Zeile gespeichert. Ein Datensatz wurde parallel geändert oder die Datenbank ist belegt. Bitte neu laden und erneut prüfen.", "danger")
            return redirect(url_for("orders.import_row", batch_id=batch.id, index=index))
    plan = row_plan(batch, index, row)
    available = options(current_user)
    return render_template("orders/import_row.html", batch=batch, row=row, index=index,
        plan=plan, entities=ENTITIES, field_labels=FIELD_LABELS, material_types=MATERIAL_TYPES,
        machine_types=MACHINE_TYPES, available=available, suggestions=suggestions(row, available),
        can_create={kind: has_permission(current_user, values[3] + ".create") for kind, values in ENTITIES.items()},
        ready=row["state"] == "ready" and not plan["errors"] and plan["fingerprint"] == row.get("fingerprint"))
