#!/usr/bin/env python3
"""Add sampling tables only. No rebuild or reclassification of existing orders."""
import sys
from pathlib import Path
from sqlalchemy import inspect, text
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.sampling.models import SamplingOrder, SamplingCheck


def run_upgrade(check_only=False):
    inspector = inspect(db.engine)
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Dieses Upgrade erwartet die FactoryOS-SQLite-Datenbank.")
    for table in ("orders", "articles", "customers", "materials", "tools", "machines", "users"):
        if not inspector.has_table(table):
            raise RuntimeError("Voraussetzung fehlt: " + table)
    order_columns = {col["name"] for col in inspector.get_columns("orders")}
    if not {"id", "order_no", "status", "is_project", "target_qty", "tool_no", "article"}.issubset(order_columns):
        raise RuntimeError("Auftragstabelle hat eine unerwartete Struktur.")
    for model in (SamplingOrder, SamplingCheck):
        if inspector.has_table(model.__tablename__):
            actual = {col["name"] for col in inspector.get_columns(model.__tablename__)}
            if not {col.name for col in model.__table__.columns}.issubset(actual):
                raise RuntimeError("Vorhandene Tabelle passt nicht zum Modell: " + model.__tablename__)
    print("Datenbank:", db.engine.url.database)
    if check_only:
        print("Strukturprüfung erfolgreich. Keine Änderungen vorgenommen.")
        return
    with db.engine.begin() as connection:
        SamplingOrder.__table__.create(bind=connection, checkfirst=True)
        SamplingCheck.__table__.create(bind=connection, checkfirst=True)
    print("Musterungsauftrags-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_upgrade("--check" in sys.argv)

