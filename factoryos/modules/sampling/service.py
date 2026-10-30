import math
from datetime import datetime, date
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm.attributes import flag_modified
from factoryos.extensions import db
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking
from .models import SamplingOrder, SamplingCheck
from .autofill_service import reference_snapshot, material_confirmed, color_signature, color_confirmed
from .definitions import (REASONS, CHECKS, INITIAL_REQUIRED, TEXT_FIELDS,
                          NUMBER_FIELDS, DATE_FIELDS, YES_NO_FIELDS)


def choices():
    return dict(articles=Article.query.order_by(Article.article_no).all(),
                customers=Customer.query.order_by(Customer.customer_no).all(),
                tools=Tool.query.order_by(Tool.tool_no).all(),
                materials=Material.query.filter(Material.material_type != "masterbatch").order_by(Material.material_no).all(),
                masterbatches=Material.query.filter_by(material_type="masterbatch").order_by(Material.material_no).all(),
                machines=Machine.query.order_by(Machine.machine_no).all(),
                previous_orders=SamplingOrder.query.order_by(SamplingOrder.id.desc()).all())


def reference(form, key, model):
    value = form.get(key, "").strip()
    if not value:
        return None
    try:
        result = db.session.get(model, int(value))
    except ValueError:
        result = None
    if result is None:
        raise ValueError("Ungültige Zuordnung: " + key)
    return result


def parse_data(form):
    data = {}
    for key in TEXT_FIELDS:
        value = form.get(key, "").strip()
        if len(value) > 10000:
            raise ValueError("Text zu lang: " + TEXT_FIELDS[key])
        data[key] = value
    for key, (label, integer) in NUMBER_FIELDS.items():
        value = form.get(key, "").strip()
        if not value:
            data[key] = None
            continue
        try:
            number = float(value.replace(",", "."))
            if not math.isfinite(number) or number < 0 or (integer and not number.is_integer()):
                raise ValueError()
        except ValueError:
            raise ValueError("Ungültiger Zahlenwert: " + label)
        data[key] = int(number) if integer else number
    percent = data.get("masterbatch_percent")
    if percent is not None and percent > 100:
        raise ValueError("Die Farbbatch-Zugabe muss zwischen 0 und 100 % liegen.")
    for key, label in DATE_FIELDS.items():
        value = form.get(key, "")
        try:
            data[key] = date.fromisoformat(value).isoformat() if value else ""
        except ValueError:
            raise ValueError("Ungültiges Datum: " + label)
    for key in YES_NO_FIELDS:
        value = form.get(key, "")
        if value not in ("", "yes", "no"):
            raise ValueError("Ungültige Ja/Nein-Auswahl.")
        data[key] = value
    return data


def save_sampling(form, user_id, sampling=None):
    creating = sampling is None
    if sampling and sampling.state == "completed":
        raise ValueError("Abgeschlossene Musterungen sind schreibgeschützt. Eine Nachbemusterung anlegen.")
    if sampling and str(sampling.version) != form.get("version"):
        raise ValueError("Der Auftrag wurde zwischenzeitlich geändert. Bitte neu laden.")
    reason = form.get("reason")
    if reason not in REASONS:
        raise ValueError("Genau einen Musterungsanlass auswählen.")
    if sampling and reason != sampling.reason:
        raise ValueError("Der Anlass ist nach Anlage unveränderlich. Für einen anderen Anlass einen separaten Auftrag anlegen.")
    number = form.get("order_no", "").strip()
    if not number or len(number) > 50:
        raise ValueError("Eine Auftragsnummer mit maximal 50 Zeichen ist erforderlich.")
    duplicate = Order.query.filter_by(order_no=number).first()
    if duplicate and (creating or duplicate.id != sampling.order_id):
        raise ValueError("Diese Auftragsnummer ist bereits vergeben.")
    try:
        quantity = int(form.get("target_qty", "0"))
        if quantity < 1:
            raise ValueError()
    except ValueError:
        raise ValueError("Die Musteranzahl muss eine positive ganze Zahl sein.")
    article = reference(form, "article_id", Article)
    tool = reference(form, "tool_id", Tool)
    customer = reference(form, "customer_id", Customer)
    material = reference(form, "material_id", Material)
    if material and material.material_type == "masterbatch":
        raise ValueError("Masterbatch bitte separat als Farbbatch auswählen.")
    machine = reference(form, "machine_id", Machine)
    previous = reference(form, "previous_id", SamplingOrder)
    if sampling and previous and previous.id != sampling.previous_id:
        raise ValueError("Die ursprüngliche Musterung kann nach Anlage nicht geändert werden.")
    data = parse_data(form)
    batch = reference(form, "masterbatch_id", Material)
    if batch and batch.material_type != "masterbatch":
        raise ValueError("Farbbatch muss aus der Kategorie Masterbatch stammen.")
    data["masterbatch_id"] = batch.id if batch else None
    if batch:
        old_data = sampling.data if sampling else {}
        same_batch = old_data.get("masterbatch_id") == batch.id
        data["masterbatch"] = old_data.get("masterbatch") if same_batch else " / ".join([batch.material_no, batch.name])
    elif form.get("masterbatch_id") is not None:
        data["masterbatch"] = ""
    else:
        data["masterbatch"] = (sampling.data or {}).get("masterbatch", "") if sampling else ""
    if data.get("masterbatch_percent") not in (None, 0) and not batch:
        raise ValueError("Bitte ein Farbbatch aus den Materialstammdaten auswählen.")
    if reason == "color_change":
        has_color = any(data.get(key) not in (None, "") for key in ("color", "ral_color", "masterbatch", "masterbatch_percent"))
        if has_color and form.get("color_confirmed") != "yes":
            raise ValueError("Farbänderung: Bitte Farbton, Farbbatch und Dosierung bewusst prüfen und bestätigen.")
        if has_color:
            data["color_confirmation"] = {
                "values": color_signature(data, article.id if article else None, material.id if material else None),
                "by_user_id": user_id, "at_utc": datetime.utcnow().isoformat(),
            }
    if reason == "material_change":
        if material and form.get("material_confirmed") != "yes":
            raise ValueError("Werkstoffänderung: Bitte den ausgewählten Rohstoff bewusst prüfen und bestätigen.")
        if material:
            data["material_confirmation"] = {
                "material_id": material.id, "article_id": article.id if article else None,
                "by_user_id": user_id, "at_utc": datetime.utcnow().isoformat(),
            }
    if reason == "other" and not data["other_reason"]:
        raise ValueError("Bitte den sonstigen Anlass erläutern.")
    active = False
    if sampling:
        active = TimeBooking.query.filter_by(order_id=sampling.order_id, end_time=None).first() is not None
        if active and (sampling.article_id != (article.id if article else None) or
                       sampling.tool_id != (tool.id if tool else None)):
            raise ValueError("Artikel und Werkzeug können während einer laufenden Buchung nicht geändert werden.")
    state = form.get("state", "draft")
    if state not in ("draft", "in_progress", "review", "rework"):
        raise ValueError("Ungültiger Bearbeitungsstatus. Abschluss nur über die Abschlussprüfung.")
    if active and state in ("draft", "rework"):
        raise ValueError("Laufende Buchung zuerst im Maschinen Booking beenden.")
    if creating:
        sampling = SamplingOrder(order=Order(order_no=number, is_project=False),
                                 reason=reason, created_by_id=user_id, snapshot={}, data={})
        db.session.add(sampling)
        sampling.checks = [SamplingCheck(key=key, status="open") for key in CHECKS]
    before = {"state": sampling.state, "data": sampling.data, "snapshot": sampling.snapshot}
    before["checks"] = {c.key: {"status": c.status, "note": c.note, "date": str(c.evidence_date or "")} for c in sampling.checks}
    snapshot = dict(sampling.snapshot or {})
    if (creating or "reference" not in snapshot or
            sampling.article_id != (article.id if article else None) or
            sampling.tool_id != (tool.id if tool else None) or
            sampling.material_id != (material.id if material else None)):
        snapshot["reference"] = reference_snapshot(article, tool, material)
    for attr, obj, number_field, name_field in (
        ("article", article, "article_no", "article_name"), ("customer", customer, "customer_no", "name"),
        ("tool", tool, "tool_no", "name"), ("material", material, "material_no", "name"),
        ("machine", machine, "machine_no", "name"),
    ):
        old_id = getattr(sampling, attr + "_id")
        new_id = obj.id if obj else None
        if creating or old_id != new_id:
            snapshot[attr] = {"number": getattr(obj, number_field), "name": getattr(obj, name_field) or ""} if obj else {}
            if attr == "article":
                snapshot["drawing_no"] = article.drawing_no if article else ""
                snapshot["drawing_revision"] = article.drawing_revision if article else ""
        setattr(sampling, attr, obj)
    sampling.previous = previous
    sampling.snapshot = snapshot
    sampling.data = data
    flag_modified(sampling, "data")
    sampling.state = state
    sampling.order.order_no = number
    sampling.order.article = snapshot.get("article", {}).get("number") or None
    sampling.order.article_name = snapshot.get("article", {}).get("name") or None
    sampling.order.tool_no = snapshot.get("tool", {}).get("number") or None
    sampling.order.target_qty = quantity
    sampling.order.status = "in_arbeit" if state in ("in_progress", "review") else "gesperrt"
    for check in sampling.checks:
        allowed = ("open", "granted", "rejected", "not_required") if check.key in ("internal", "external") else ("open", "done", "rejected", "not_required")
        value = form.get("check_" + check.key, "open")
        if value not in allowed:
            raise ValueError("Ungültiger Prüfstatus.")
        note = form.get("note_" + check.key, "").strip()
        if len(note) > 5000:
            raise ValueError("Prüfnotiz zu lang.")
        raw_date = form.get("date_" + check.key, "")
        try:
            evidence_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError:
            raise ValueError("Ungültiges Prüfdatum.")
        if value in ("done", "granted", "rejected") and evidence_date is None:
            raise ValueError("Bitte ein Datum angeben: " + CHECKS[check.key])
        if value in ("rejected", "not_required") and not note:
            raise ValueError("Bitte Ablehnung oder 'nicht erforderlich' begründen: " + CHECKS[check.key])
        if (value, note, evidence_date) != (check.status, check.note or "", check.evidence_date):
            check.updated_by_id = user_id
            check.updated_at = datetime.utcnow()
        check.status, check.note, check.evidence_date = value, note, evidence_date
    db.session.flush()
    log_change("sampling", sampling.id, "create" if creating else "update",
               entity_name=number, category="orders", changes={"record": {"old": before, "new": {
                   "state": state, "data": data, "snapshot": snapshot,
                   "checks": {c.key: {"status": c.status, "note": c.note, "date": str(c.evidence_date or "")} for c in sampling.checks}
               }}})
    db.session.commit()
    return sampling


def completion_errors(sampling):
    errors = []
    if sampling.reason == "color_change" and not color_confirmed(sampling):
        errors.append("Farbänderung: Gewünschten Farbton oder RAL angeben und Farbangaben bewusst bestätigen.")
    if sampling.reason == "material_change" and not material_confirmed(sampling):
        errors.append("Werkstoffänderung: Versuchsmaterial muss bewusst bestätigt werden.")
    if sampling.state != "review":
        errors.append("Vor dem Abschluss den Status auf In Prüfung setzen.")
    data = sampling.data or {}
    checks = {c.key: c for c in sampling.checks}
    if not all((sampling.article_id, sampling.tool_id, sampling.material_id, sampling.machine_id)):
        errors.append("Artikel, Werkzeug, Rohstoff und Maschine müssen zugeordnet sein.")
    if not data.get("sampled_date") or not data.get("operator"):
        errors.append("Durchführungsdatum und durchführende Person fehlen.")
    if not data.get("changes_result"):
        errors.append("Änderungen / Ergebnis dokumentieren.")
    if TimeBooking.query.filter_by(order_id=sampling.order_id, end_time=None).first():
        errors.append("Die laufende Maschinenbuchung zuerst beenden.")
    for key, label in CHECKS.items():
        check = checks.get(key)
        if key == "external" and sampling.reason != "initial":
            continue
        allowed = ("granted",) if key in ("internal", "external") else ("done", "not_required")
        if sampling.reason == "initial" and key in INITIAL_REQUIRED:
            allowed = ("done",)
        if not check or check.status not in allowed:
            errors.append(label + ": Abschlussvoraussetzung nicht erfüllt.")
    if sampling.reason == "initial":
        if not sampling.customer_id:
            errors.append("Erstbemusterung: Kunde ist erforderlich.")
        for key in ("initial_scope", "initial_evidence", "cavity_result"):
            if not data.get(key):
                errors.append("Erstbemusterung: " + TEXT_FIELDS[key] + " fehlt.")
    return errors


def complete_sampling(sampling, user_id):
    if sampling.state == "completed":
        raise ValueError("Diese Musterung ist bereits abgeschlossen.")
    errors = completion_errors(sampling)
    if errors:
        raise ValueError(" ".join(errors))
    sampling.state = "completed"
    sampling.order.status = "fertig"
    sampling.completed_at = datetime.utcnow()
    sampling.completed_by_id = user_id
    log_change("sampling", sampling.id, "complete", category="orders",
               entity_name=sampling.order.order_no,
               changes={"result": {"old": "offen", "new": "Erfolgreich abgeschlossen"}})
    db.session.commit()

