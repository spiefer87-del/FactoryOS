"""Review first, commit a single confirmed row atomically. Never mutate existing masters."""
from copy import deepcopy
from datetime import date, datetime
from difflib import SequenceMatcher
import hashlib
import json
import re
from sqlalchemy import or_
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.orders.models import Order
from factoryos.modules.orders.import_models import ERPOrderData
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.machines.models import Machine
from factoryos.modules.production.models import TimeBooking, QuantityReport
from factoryos.modules.masterdata.shared.constants import MACHINE_TYPES
from .erp_excel_reader import clean, quantity, iso_date
from .cycle_time import parse_cycle_time, valid_cycle_time

ENTITIES = {
    "customer": (Customer, "customer_no", "name", "customers", "Kunde", False),
    "tool": (Tool, "tool_no", "name", "tools", "Werkzeug", False),
    "material": (Material, "material_no", "name", "materials", "Rohstoff", False),
    "machine": (Machine, "machine_no", "name", "machines", "Maschine", False),
    "article": (Article, "article_no", "article_name", "articles", "Artikel", True),
}
MATERIAL_TYPES = {"plastic": "Kunststoff", "masterbatch": "Masterbatch / Farbbatch",
                  "operating": "Betriebsstoff", "auxiliary": "Hilfsstoff"}
FIELD_LABELS = {
    "order_no": "Fertigungsauftragsnummer", "article_no": "Artikelnummer",
    "article_name": "Artikelbezeichnung", "quantity": "Fertigungsmenge (Stück)",
    "cycle_time_s": "Soll-Zykluszeit (Sekunden pro Maschinenzyklus, Pflicht)",
    "customer_no": "Kundennummer", "customer_name": "Kundenname",
    "tool_no": "Werkzeugnummer", "tool_name": "Werkzeugbezeichnung",
    "material_no": "Materialnummer", "material_name": "Materialbezeichnung",
    "machine_no": "Maschinennummer", "machine_name": "Maschinenname",
    "delivery_date": "Lieferdatum (optional, JJJJ-MM-TT)",
    "delivery_week": "Liefer-KW (optional, z. B. 44/26)", "unit": "Mengeneinheit",
}

def options(user):
    result = {}
    for kind, (model, number, name, group, label, required) in ENTITIES.items():
        result[kind] = [{"id": obj.id, "number": getattr(obj, number), "name": getattr(obj, name) or ""}
                        for obj in model.query.order_by(getattr(model, number)).all()] if has_permission(user, group + ".view") else []
    return result

def default_choices(row, user):
    row = deepcopy(row)
    row["fields"].setdefault("machine_name", "")
    row["fields"].setdefault("machine_type", "injection_molding")
    for kind, (model, number, name, group, label, required) in ENTITIES.items():
        if kind in row["choices"]:
            continue
        value = row["fields"].get(number, "")
        matches = model.query.filter(getattr(model, number) == value).all() if value and has_permission(user, group + ".view") else []
        if not matches and value and has_permission(user, group + ".view") and hasattr(model, "external_" + number):
            matches = model.query.filter(getattr(model, "external_" + number) == value).all()
        row["choices"][kind] = "id:" + str(matches[0].id) if len(matches) == 1 else ("none" if not value and not required else "")
    article_choice = row["choices"].get("article", "")
    if article_choice.startswith("id:") and has_permission(user, "articles.view"):
        try: article = db.session.get(Article, int(article_choice[3:]))
        except (ValueError, OverflowError): article = None
        if article:
            if not row.get("reviewed") and not row["fields"].get("cycle_time_s") and valid_cycle_time(article.cycle_time_s):
                row["fields"]["cycle_time_s"] = str(article.cycle_time_s)
            for kind, obj in (("customer", article.customer), ("material", article.material),
                              ("tool", article.tools[0] if len(article.tools) == 1 else None)):
                model, number, name, group, label, required = ENTITIES[kind]
                if obj and not row["fields"].get(number) and has_permission(user, group + ".view"):
                    # Only enrich untouched rows, never undo an explicit user decision.
                    original = next((cell["value"] for cell in row["source"] if cell["label"] == {"customer":"Kundennummer", "material":"Material", "tool":"Werkzeug"}[kind]), "")
                    if not original and not row.get("reviewed"):
                        row["fields"][number] = getattr(obj, number)
                        row["fields"][kind + "_name"] = getattr(obj, name) or ""
                        row["choices"][kind] = "id:" + str(obj.id)
    return row

def suggestions(row, available):
    result = {}
    for kind, (_, number, name, group, label, required) in ENTITIES.items():
        incoming = row["fields"].get(number, "").casefold()
        incoming_name = row["fields"].get(kind + "_name", "").casefold()
        def score(item):
            return max(SequenceMatcher(None, incoming, item["number"].casefold()).ratio() if incoming else 0,
                       SequenceMatcher(None, incoming_name, item["name"].casefold()).ratio() if incoming_name else 0)
        result[kind] = sorted([item for item in available[kind] if score(item) >= .4],
                              key=lambda item: (-score(item), item["number"]))[:5]
    return result

def model_snapshot(obj):
    if obj is None:
        return None
    values = {column.name: clean(getattr(obj, column.name)) for column in obj.__table__.columns}
    if isinstance(obj, Article):
        values["tool_ids"] = sorted(tool.id for tool in obj.tools)
    return values

def build_plan(row, user):
    row = deepcopy(row)
    fields = row["fields"]
    errors, warnings, resolved, master_changes = [], [], {}, []
    def error(text): errors.append(text)
    limits = {"order_no": 50, "article_no": 50, "article_name": 200,
              "customer_no": 50, "customer_name": 200, "tool_no": 50, "tool_name": 100,
              "material_no": 100, "material_name": 200, "machine_no": 100, "machine_name": 150,
              "delivery_week": 20, "unit": 30}
    for key, limit in limits.items():
        fields[key] = clean(fields.get(key))
        if len(fields[key]) > limit: error(f"{FIELD_LABELS.get(key, key)}: maximal {limit} Zeichen.")
    if not fields["order_no"]: error("Fertigungsauftragsnummer fehlt.")
    try: cycle = parse_cycle_time(fields.get("cycle_time_s"))
    except ValueError as ex: error(str(ex)); cycle = None
    try: amount = quantity(fields.get("quantity"))
    except ValueError as ex: error(str(ex)); amount = None
    if fields["unit"].casefold() not in ("stück", "stueck", "stk", "st", "pcs", "piece", "pieces"):
        error("Mengeneinheit bitte ausdrücklich als Stück bestätigen. Keine automatische kg-/Stück-Umrechnung.")
    parsed_date = None
    try:
        fields["delivery_date"] = iso_date(fields.get("delivery_date"))
        if fields["delivery_date"]: parsed_date = date.fromisoformat(fields["delivery_date"])
    except ValueError as ex: error("Lieferdatum: " + str(ex))
    if parsed_date:
        if parsed_date < date.today():
            warnings.append("Das Lieferdatum liegt in der Vergangenheit.")
    week = fields.get("delivery_week", "")
    if week:
        match = re.fullmatch(r"(\d{1,2})/(\d{2}|\d{4})", week)
        try:
            if not match: raise ValueError()
            year = int(match[2]) + (2000 if len(match[2]) == 2 else 0)
            monday = date.fromisocalendar(year, int(match[1]), 1)
            if monday.fromordinal(monday.toordinal() + 6) < date.today():
                warnings.append("Die Liefer-KW liegt bereits in der Vergangenheit.")
            if parsed_date:
                stamp = parsed_date.isocalendar()
                if (stamp.year, stamp.week) != (year, int(match[1])):
                    warnings.append("Lieferdatum und Liefer-KW widersprechen sich.")
        except ValueError: error("Liefer-KW bitte als Woche/Jahr eingeben, z. B. 44/26.")
        warnings.append("Die Liefer-KW bleibt eine Kalenderwoche; daraus wird kein verbindliches Tagesdatum berechnet.")
    if not row.get("acknowledged"):
        error("Bitte ERP-Auftragsart, Status, Zuordnungen und Hinweise ausdrücklich bestätigen.")
    warnings.append("ERP-Auftragsart und ERP-Status bleiben als Originalwerte erhalten. Kein Produktionsstart und keine automatische Statusübernahme.")
    for kind, (model, number, name, group, label, required) in ENTITIES.items():
        choice = row["choices"].get(kind, "")
        record = {"kind": kind, "label": label, "mode": "", "number": fields.get(number, ""), "name": fields.get(kind + "_name", "")}
        if choice == "none" and not required:
            record["mode"] = "none"
            if record["number"]: warnings.append(f"{label}: ERP-Angabe wird bewusst ohne Stammdatenzuordnung übernommen.")
        elif choice == "new":
            record["mode"] = "new"
            if not has_permission(user, group + ".create"): error(f"Keine Berechtigung: {label} anlegen.")
            if not record["number"] or not record["name"]: error(f"{label}: Nummer und Bezeichnung für Neuanlage erforderlich.")
            if record["number"] and model.query.filter(getattr(model, number) == record["number"]).first():
                error(f"{label}: Nummer existiert bereits. Vorhandenen Datensatz auswählen.")
            if kind == "material" and fields.get("material_type") not in MATERIAL_TYPES: error("Materialkategorie ist ungültig.")
            if kind == "machine" and fields.get("machine_type") not in MACHINE_TYPES: error("Maschinentyp ist ungültig.")
            if kind == "tool":
                warnings.append("Neues Werkzeug erhält nur geprüfte Nummer/Bezeichnung. Technische Daten und Werkzeugfreigabe bitte anschließend pflegen.")
            master_changes.append(f"{label} neu anlegen: {record['number']} – {record['name']}")
        elif choice.startswith("id:"):
            if not has_permission(user, group + ".view"):
                error(f"Keine Berechtigung: {label}-Stammdaten lesen.")
                resolved[kind] = record
                continue
            try: obj = db.session.get(model, int(choice[3:]))
            except (ValueError, OverflowError): obj = None
            if obj is None:
                error(f"{label}: ausgewählter Datensatz fehlt.")
            else:
                record.update(mode="existing", id=obj.id, number=getattr(obj, number), name=getattr(obj, name) or "", snapshot=model_snapshot(obj))
                if fields.get(number) and fields[number] != record["number"]:
                    warnings.append(f"{label}: ERP-Nummer {fields[number]} wird ausdrücklich {record['number']} zugeordnet.")
                if fields.get(kind + "_name") and fields[kind + "_name"].casefold() != record["name"].casefold():
                    warnings.append(f"{label}: Bezeichnung weicht ab. Bestehender Stammsatz bleibt unverändert.")
                if hasattr(obj, "active") and not obj.active:
                    error(f"{label}: Datensatz ist inaktiv. Bitte im Stammdatenmodul prüfen.")
                if isinstance(obj, Article) and obj.status != "active": error("Artikel ist nicht aktiv.")
                if isinstance(obj, Tool) and obj.tool_status not in (None, "aktiv", "active"): error("Werkzeug ist nicht aktiv/verfügbar. Bitte Stammdaten prüfen.")
                if isinstance(obj, Material) and obj.material_status != "aktiv": error("Material ist nicht aktiv.")
        else:
            error(f"{label}: bitte vorhandenen Datensatz auswählen, Neuanlage bestätigen oder bewusst ohne Zuordnung fortfahren.")
        resolved[kind] = record
        if kind == "tool" and record.get("mode") == "existing" and len(record["number"]) > 50:
            error("Die gewählte Werkzeugnummer ist länger als das aktuelle Auftragsfeld (50 Zeichen). Bitte Stammdaten prüfen.")
    article = resolved["article"]
    if article.get("mode") == "existing":
        snapshot = article["snapshot"]
        for kind, fk in (("customer", "customer_id"), ("material", "material_id")):
            record = resolved[kind]
            if snapshot.get(fk) and (record.get("mode") != "existing" or str(record.get("id")) != snapshot[fk]):
                warnings.append(f"Artikelstamm: {ENTITIES[kind][4]} weicht von der Auftragszuordnung ab. Nur der Auftrag erhält die gewählte Zuordnung.")
        tool = resolved["tool"]
        if snapshot.get("tool_ids") and (tool.get("mode") != "existing" or tool.get("id") not in snapshot["tool_ids"]):
            warnings.append("Werkzeug ist dem vorhandenen Artikel nicht zugeordnet. Der Artikelstamm wird nicht verändert.")
    existing = Order.query.filter_by(order_no=fields["order_no"]).first()
    action = row.get("action", "create")
    if existing:
        if action != "update": error("Auftragsnummer existiert bereits. Bewusst Aktualisieren wählen oder Zeile überspringen.")
        if not has_permission(user, "orders.edit"): error("Keine Berechtigung zum Aktualisieren von Aufträgen.")
        if existing.sampling or existing.is_project: error("Musterungs- und Projektaufträge dürfen hier nicht verändert werden.")
        if existing.status not in ("open", "offen"): error("Nur offene, ungebuchte Fertigungsaufträge dürfen aktualisiert werden.")
        if TimeBooking.query.filter_by(order_id=existing.id).first() or QuantityReport.query.filter_by(order_id=existing.id).first():
            error("Auftrag hat bereits Zeit- oder Mengenbuchungen und bleibt unverändert.")
    else:
        if action == "update": error("Auftrag ist nicht vorhanden. Neu anlegen wählen.")
        if not has_permission(user, "orders.create"): error("Keine Berechtigung zum Anlegen von Aufträgen.")
    changes = []
    target = {"article": article.get("number", ""), "article_name": article.get("name", ""),
              "tool_no": resolved["tool"].get("number", "") if resolved["tool"]["mode"] != "none" else None,
              "target_qty": amount, "cycle_time_s": cycle}
    if existing:
        for key, value in target.items():
            if getattr(existing, key) != value:
                changes.append({"field": key, "before": clean(getattr(existing, key)), "after": clean(value)})
    digest_data = {"fields": fields, "resolved": resolved, "order": model_snapshot(existing),
                   "action": action, "user": user.id, "errors": errors, "warnings": warnings}
    fingerprint = hashlib.sha256(json.dumps(digest_data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"errors": errors, "warnings": warnings, "resolved": resolved, "fields": fields,
            "fingerprint": fingerprint, "changes": changes, "new_masters": master_changes,
            "order_id": existing.id if existing else None, "target": target, "action": action}

def commit_plan(row, plan, batch, user):
    """Caller owns transaction and batch version lock; all writes roll back together."""
    entities, references = {}, {}
    for kind, (model, number, name, group, label, required) in ENTITIES.items():
        record = plan["resolved"][kind]
        obj = None
        if record["mode"] == "existing":
            obj = db.session.get(model, record["id"])
        elif record["mode"] == "new":
            values = {number: record["number"], name: record["name"]}
            if kind in ("tool", "material", "machine"):
                values["created_by_id"] = user.id
            if kind == "tool":
                values.update(created_at=datetime.utcnow(), tool_status="aktiv")
            if kind == "material": values["material_type"] = plan["fields"]["material_type"]
            if kind == "machine": values["machine_type"] = plan["fields"]["machine_type"]
            if kind == "article":
                values.update(customer=entities.get("customer"), material=entities.get("material"))
            obj = model(**values)
            if kind == "article" and entities.get("tool"): obj.tools.append(entities["tool"])
            db.session.add(obj)
            db.session.flush()
            log_change(entity_type=kind, entity_id=obj.id, entity_name=record["number"], action="import",
                       changes={"source": {"old": None, "new": f"ERP-Import {batch.filename}, Zeile {row['excel_row']}"}},
                       category="masterdata")
        entities[kind] = obj
        references[kind] = {"id": obj.id if obj else None, "number": record["number"], "name": record["name"],
                            "mode": record["mode"]}
    order = db.session.get(Order, plan["order_id"]) if plan["order_id"] else Order(order_no=plan["fields"]["order_no"], status="open")
    old = model_snapshot(order) if order.id else None
    for key, value in plan["target"].items(): setattr(order, key, value)
    db.session.add(order)
    db.session.flush()
    if order.erp_import is None: order.erp_import = ERPOrderData(imported_by_id=user.id, snapshot={})
    previous = order.erp_import.snapshot
    # Current snapshot plus a compact history retain earlier source versions.
    history = list(previous.get("history", [])) if previous else []
    if previous:
        history.append({key: value for key, value in previous.items() if key != "history"})
    order.erp_import.snapshot = {
        "filename": batch.filename, "sheet": batch.sheet, "excel_row": row["excel_row"],
        "source": row["source"], "fields": plan["fields"], "references": references,
        "warnings_confirmed": plan["warnings"], "history": history,
    }
    order.erp_import.imported_by_id = user.id
    order.erp_import.imported_at = datetime.utcnow()
    log_change(entity_type="order", entity_id=order.id, entity_name=order.order_no, action="import",
               changes={"erp_import": {"old": old, "new": {**plan["target"], "batch": batch.id}}},
               category="orders")
    db.session.flush()
    return order
