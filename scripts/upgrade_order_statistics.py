#!/usr/bin/env python3
"""Register only the correction permission. No schema or role-grant changes."""
import sys
from pathlib import Path
from sqlalchemy import inspect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.admin.permissions.models import Permission

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table,required in {
        "orders":{"id","cycle_time_s","target_qty"},"time_bookings":{"id","order_id","machine_id","start_time","end_time","process","type"},
        "quantity_reports":{"id","good_qty","scrap_qty","created_at"},"change_logs":{"id","changes","user_id"},
        "permissions":{"id","name","description"}
    }.items():
        if not inspector.has_table(table) or not required.issubset({column["name"] for column in inspector.get_columns(table)}):
            raise RuntimeError(f"Tabelle {table} fehlt oder ist nicht kompatibel. Vorherige Patches bitte vollständig installieren.")
    if check_only:
        print("Auftragsstatistik: Strukturprüfung erfolgreich. Keine Änderung.")
        return
    if not Permission.query.filter_by(name="production.edit_booking_time").first():
        db.session.add(Permission(name="production.edit_booking_time",
            description="Tatsächliche Produktions-Startzeiten mit Vorschau, Begründung und Änderungsprotokoll korrigieren."))
    db.session.commit()
    print("Statistik-/Startzeit-Upgrade abgeschlossen. Bestehende Rollenrechte und Buchungen bleiben unverändert.")
    print("Neues Recht Startzeiten korrigieren bei Bedarf bewusst zuweisen.")

if __name__=="__main__":
    app=create_app()
    with app.app_context():run_upgrade("--check" in sys.argv)
