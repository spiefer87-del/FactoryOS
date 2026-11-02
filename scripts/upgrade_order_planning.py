#!/usr/bin/env python3
"""Add plan tables/catalog only. Preserve every operational record and role grant."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import ProductionPlanningState,MachinePlanningSettings,ProductionPlanEntry
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name not in ("sqlite","postgresql"):raise RuntimeError("Nicht unterstützte Datenbank.")
    required={"machines":{"id","machine_no","machine_status"},"orders":{"id","cycle_time_s","target_qty"},
        "users":{"id","role_id"},"time_bookings":{"id","machine_id","order_id","start_time","end_time"},
        "machine_control_lock":{"id","version"},"machine_control_states":{"machine_id","resume_order_id"},
        "machine_control_commands":{"id","command_id"},"permissions":{"id","name","description"},
        "change_logs":{"id","changes","user_id"}}
    for table,columns in required.items():
        if not inspector.has_table(table) or not columns.issubset({c["name"] for c in inspector.get_columns(table)}):
            raise RuntimeError(f"Tabelle {table} fehlt oder ist inkompatibel. Maschinenbedienung und vorherige Patches zuerst vollständig installieren.")
    models=(ProductionPlanningState,MachinePlanningSettings,ProductionPlanEntry)
    for model in models:
        if inspector.has_table(model.__tablename__) and not set(model.__table__.columns.keys()).issubset({c["name"] for c in inspector.get_columns(model.__tablename__)}):
            raise RuntimeError(f"Unvollständige Tabelle {model.__tablename__}. Keine automatische Reparatur.")
    print("Auftragsplanung: Strukturprüfung erfolgreich.")
    if check_only:return
    for model in models:model.__table__.create(bind=db.engine,checkfirst=True)
    for index in ProductionPlanEntry.__table__.indexes:index.create(bind=db.engine,checkfirst=True)
    if not db.session.get(ProductionPlanningState,1):db.session.add(ProductionPlanningState(id=1,version=0))
    if not Permission.query.filter_by(name="production.plan").first():
        db.session.add(Permission(name="production.plan",description=PERMISSION_TEXT["production.plan"]["description"]))
    db.session.commit()
    print("Planung vorbereitet. Keine Aufträge, Buchungen, Mengen oder Rollenrechte geändert.")
    print("Neues Recht Aufträge planen für die Fertigungsleitung bewusst zuweisen; Admin hat Zugriff.")

if __name__=="__main__":
    app=create_app()
    with app.app_context():run_upgrade("--check" in sys.argv)
