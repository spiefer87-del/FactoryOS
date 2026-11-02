#!/usr/bin/env python3
"""Add the nullable order target-cycle column; preserve all historical values."""
import sys
from pathlib import Path
from sqlalchemy import inspect, text, Float, Numeric, Integer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db


def run_upgrade(check_only=False, engine=None):
    engine = engine if engine is not None else db.engine
    inspector = inspect(engine)
    if engine.dialect.name != "sqlite":
        raise RuntimeError("Dieses Upgrade erwartet SQLite.")
    if not inspector.has_table("orders"):
        raise RuntimeError("Auftragstabelle fehlt.")
    columns = {column["name"]: column for column in inspector.get_columns("orders")}
    if not {"id", "order_no", "target_qty", "status"}.issubset(columns):
        raise RuntimeError("Auftragstabelle ist nicht kompatibel.")
    if "cycle_time_s" in columns and not columns["cycle_time_s"]["nullable"]:
        raise RuntimeError("Unerwartete Zykluszeitspalte: Altaufträge müssen NULL erlauben.")
    if "cycle_time_s" in columns and not isinstance(columns["cycle_time_s"]["type"], (Float, Numeric, Integer)):
        raise RuntimeError("Unerwarteter Datentyp der vorhandenen Zykluszeitspalte.")
    if check_only:
        print("Soll-Zykluszeit: Strukturprüfung erfolgreich. Keine Änderung.")
        return
    if "cycle_time_s" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE orders ADD COLUMN cycle_time_s FLOAT"))
    print("Soll-Zykluszeit-Upgrade abgeschlossen. Keine historischen Sollwerte erfunden; Altaufträge bleiben unverändert.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context(): run_upgrade("--check" in sys.argv)
