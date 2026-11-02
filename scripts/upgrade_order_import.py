#!/usr/bin/env python3
"""Add two ERP-only tables and one permission; no existing columns or role grants change."""
import sys
from pathlib import Path
from sqlalchemy import inspect
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.orders.import_models import ERPImportBatch, ERPOrderData
from factoryos.modules.admin.permissions.models import Permission


def run_upgrade(check_only=False):
    inspector = inspect(db.engine)
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Dieses Upgrade erwartet SQLite.")
    for table, required in (("orders", {"id", "order_no", "article", "tool_no", "status", "target_qty"}),
                            ("users", {"id"}), ("permissions", {"id", "name", "description"})):
        if not inspector.has_table(table) or not required.issubset({c["name"] for c in inspector.get_columns(table)}):
            raise RuntimeError(f"Tabelle {table} fehlt oder ist nicht kompatibel.")
    for model in (ERPImportBatch, ERPOrderData):
        if inspector.has_table(model.__tablename__):
            if not {c.name for c in model.__table__.columns}.issubset({c["name"] for c in inspector.get_columns(model.__tablename__)}):
                raise RuntimeError(f"Vorhandene Tabelle {model.__tablename__} ist nicht kompatibel.")
            actual_pk = set(inspector.get_pk_constraint(model.__tablename__)["constrained_columns"])
            expected_pk = {column.name for column in model.__table__.primary_key}
            if actual_pk != expected_pk: raise RuntimeError("Unerwarteter Primärschlüssel.")
    if check_only:
        print("ERP-Import: Strukturprüfung erfolgreich. Keine Änderungen vorgenommen.")
        return
    with db.engine.begin() as connection:
        ERPImportBatch.__table__.create(bind=connection, checkfirst=True)
        ERPOrderData.__table__.create(bind=connection, checkfirst=True)
    if not Permission.query.filter_by(name="orders.excel_import").first():
        db.session.add(Permission(name="orders.excel_import", description="ERP-Aufträge mit Vorschau prüfen und nach ausdrücklicher Bestätigung importieren. Zusätzliche Anlage-/Bearbeitungsrechte gelten."))
    db.session.commit()
    print("ERP-Import-Upgrade abgeschlossen. Bestehende Aufträge/Stammdaten und Rollenrechte bleiben unverändert.")
    print("Das neue Recht orders.excel_import bei Bedarf in der Rechteverwaltung zuweisen.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context(): run_upgrade("--check" in sys.argv)
