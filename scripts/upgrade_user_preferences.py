#!/usr/bin/env python3
"""Create only the user_preferences table. Existing tables/data remain untouched."""
import sys
from pathlib import Path
from sqlalchemy import inspect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.profile.models import UserPreference


def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name!="sqlite":
        raise RuntimeError("Dieses Upgrade erwartet SQLite.")
    if not inspector.has_table("users") or "id" not in {c["name"] for c in inspector.get_columns("users")}:
        raise RuntimeError("Benutzertabelle fehlt oder ist nicht kompatibel.")
    if inspector.has_table("user_preferences"):
        actual={c["name"] for c in inspector.get_columns("user_preferences")}
        if not {c.name for c in UserPreference.__table__.columns}.issubset(actual):
            raise RuntimeError("Vorhandene Einstellungstabelle ist nicht kompatibel.")
        if set(inspector.get_pk_constraint("user_preferences")["constrained_columns"])!={"user_id","section"}:
            raise RuntimeError("Unerwarteter Primärschlüssel der Einstellungstabelle.")
    if check_only:
        print("Strukturprüfung erfolgreich. Keine Änderungen vorgenommen.")
        return
    with db.engine.begin() as conn:
        UserPreference.__table__.create(bind=conn,checkfirst=True)
    print("Benutzereinstellungs-Upgrade erfolgreich abgeschlossen.")


if __name__=="__main__":
    app=create_app()
    with app.app_context():
        run_upgrade("--check" in sys.argv)
