#!/usr/bin/env python3
"""Add command receipts/recovery state. Never rewrite existing time bookings."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,func
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking,MachineControlLock,MachineControlState,MachineControlCommand
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name not in ("sqlite","postgresql"):
        raise RuntimeError("Nicht unterstützte Datenbank für die Maschinensteuerung.")
    for table,columns in {
        "machines":{"id","machine_no","machine_status"},"users":{"id","active","role_id"},
        "orders":{"id","order_no","cycle_time_s"},"permissions":{"id","name","description"},
        "time_bookings":{"id","machine_id","order_id","process","type","start_time","end_time","prev_order_id"},
        "change_logs":{"id","changes","user_id"},
    }.items():
        if not inspector.has_table(table) or not columns.issubset({c["name"] for c in inspector.get_columns(table)}):
            raise RuntimeError(f"Tabelle {table} fehlt oder ist nicht kompatibel. Vorherige Patches vollständig installieren.")
    for model in (MachineControlLock,MachineControlState,MachineControlCommand):
        if inspector.has_table(model.__tablename__) and not set(model.__table__.columns.keys()).issubset({c["name"] for c in inspector.get_columns(model.__tablename__)}):
            raise RuntimeError(f"Unvollständige Tabelle {model.__tablename__}. Keine automatische Reparatur.")
    conflicts=db.session.query(TimeBooking.machine_id,func.count(TimeBooking.id)).filter(
        TimeBooking.machine_id.isnot(None),TimeBooking.end_time.is_(None)).group_by(TimeBooking.machine_id).having(func.count(TimeBooking.id)>1).all()
    print(f"Strukturprüfung erfolgreich. Maschinen mit mehrfach aktiven Altbuchungen: {len(conflicts)}.")
    for machine_id,total in conflicts:print(f"  Maschine #{machine_id}: {total} aktive Buchungen; Bedienung bleibt bis zur Klärung gesperrt.")
    if check_only:return
    for model in (MachineControlLock,MachineControlState,MachineControlCommand):
        model.__table__.create(bind=db.engine,checkfirst=True)
    if not db.session.get(MachineControlLock,1):db.session.add(MachineControlLock(id=1,version=0))
    for name in ("production.clear_fault","production.maintenance"):
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]["description"]))
    db.session.commit()
    print("Maschinenbedienung vorbereitet. Alte Buchungen und Rollenrechte bleiben unverändert.")
    print("Neue Rechte Entstören und Wartung bewusst in der Rechteverwaltung zuweisen. Admin hat Zugriff.")

if __name__=="__main__":
    app=create_app()
    with app.app_context():run_upgrade("--check" in sys.argv)
