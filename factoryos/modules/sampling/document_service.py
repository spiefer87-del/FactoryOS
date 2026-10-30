"""Saved sampling records as a shared, read-only print/PDF document."""
from datetime import date, datetime
from .definitions import REASONS, STATES, CHECKS, CHECK_STATUSES, TEXT_FIELDS, NUMBER_FIELDS, DATE_FIELDS, YES_NO_FIELDS
from factoryos.extensions import db
from factoryos.models.user import User


def display(value):
    if value is None or value == "":
        return "-"
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, float):
        return f"{value:g}".replace(".", ",")
    return str(value)


def date_value(value):
    try:
        return date.fromisoformat(str(value)).strftime("%d.%m.%Y") if value else "-"
    except ValueError:
        return display(value)


def document_data(record):
    data = record.data or {}
    snapshot = record.snapshot or {}
    creator = db.session.get(User, record.created_by_id)
    completed_by = db.session.get(User, record.completed_by_id) if record.completed_by_id else None

    def ref(key):
        value = snapshot.get(key) or {}
        return " / ".join(str(value.get(k)) for k in ("number", "name") if value.get(k)) or "-"

    status = STATES.get(record.state, record.state)
    if record.state == "completed" and record.reason != "initial":
        status = "Intern erfolgreich abgeschlossen"
    basics = [
        ("Ersteller", creator.username if creator else "-"),
        ("Erstellt am (UTC)", record.created_at.strftime("%d.%m.%Y %H:%M") if record.created_at else "-"),
        ("Kunde", ref("customer")), ("Artikel", ref("article")),
        ("Werkzeug", ref("tool")), ("Maschine", ref("machine")),
        ("Musteranzahl", display(record.order.target_qty)),
        ("Zeichnung / Index", f"{snapshot.get('drawing_no') or '-'} / {snapshot.get('drawing_revision') or '-'}"),
        ("Kunden-Auftragsnummer", display(data.get("customer_order"))),
        ("Geplanter Termin", date_value(data.get("planned_date"))),
        ("Vorherige Musterung", record.previous.order.order_no if record.previous else "-"),
    ]
    material = [("Rohstoff", ref("material")),
                ("Farbe", display(data.get("color"))), ("Zusätze / Anteil", display(data.get("additives")))]
    material += [(YES_NO_FIELDS[key], {"yes": "Ja", "no": "Nein"}.get(data.get(key), "Offen"))
                 for key in ("drawing_available", "customer_material", "dry_material")]
    execution = [("Durchgeführt von", display(data.get("operator"))),
                 ("Bemustert am", date_value(data.get("sampled_date"))),
                 ("Einrichter", display(data.get("setter")))]
    execution += [(label, display(data.get(key))) for key, (label, _) in NUMBER_FIELDS.items()]
    setup, sampling = data.get("setup_minutes"), data.get("sampling_minutes")
    execution += [("Gesamtaufwand (Minuten)", display(setup + sampling) if setup is not None and sampling is not None else "Nicht vollständig erfasst"),
                  ("Datumstempel", {"yes": "Ja", "no": "Nein"}.get(data.get("date_stamp"), "Offen")),
                  ("Datumsanzeige bis", date_value(data.get("date_stamp_until")))]
    groups = [
        {"title": "01  Auftrag und Zuordnungen", "rows": basics, "texts": []},
        {"title": "02  Material und Vorgaben", "rows": material,
         "texts": [(TEXT_FIELDS[key], display(data.get(key))) for key in ("other_reason", "instructions")
                   if key != "other_reason" or data.get(key)]},
        {"title": "03  Durchführung und Ergebnis", "rows": execution,
         "texts": [(TEXT_FIELDS[key], display(data.get(key))) for key in
                   ("changes_result", "deviations", "packaging_proposal", "delivery_note")]},
    ]
    if record.reason == "initial" or any(data.get(k) for k in ("initial_scope", "cavity_result", "initial_evidence")):
        groups.append({"title": "04  Erweiterte Erstbemusterung", "rows": [],
                       "texts": [(TEXT_FIELDS[key], display(data.get(key)))
                                 for key in ("initial_scope", "cavity_result", "initial_evidence")]})
    checks_by_key = {c.key: c for c in record.checks}
    checks = []
    for key, label in CHECKS.items():
        check = checks_by_key.get(key)
        checks.append({"key": key, "label": label,
                       "status": CHECK_STATUSES.get(check.status, check.status) if check else "Offen",
                       "date": display(check.evidence_date) if check else "-",
                       "user": check.updated_by.username if check and check.updated_by else "-",
                       "note": check.note if check and check.note else ""})
    completed = record.completed_at.strftime("%d.%m.%Y %H:%M") + " UTC" if record.completed_at else "-"
    return dict(number=record.order.order_no, reason=REASONS.get(record.reason, record.reason),
                status=status, version=record.version, generated=datetime.utcnow().strftime("%d.%m.%Y %H:%M UTC"),
                groups=groups, checks=checks,
                closing=[("Abschlussstatus", status), ("Abgeschlossen am", completed),
                         ("Abgeschlossen durch", completed_by.username if completed_by else "-")],
                closing_texts=[(TEXT_FIELDS[key], display(data.get(key))) for key in ("quality_note", "actions")],
                notice=("Erstbemusterung: Interne und externe Freigabe sind für den erfolgreichen Abschluss erforderlich."
                        if record.reason == "initial" else
                        "Interner Abschluss und externe Kundenfreigabe sind getrennte Entscheidungen. Der Kundenstatus steht in der Prüfliste."),
                preliminary=record.state != "completed")

