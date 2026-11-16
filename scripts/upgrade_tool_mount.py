#!/usr/bin/env python3
"""Only new tooling/setup tables, no assumptions or rewrites of historical data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import MachineToolState,SetupOperation


def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table in ('machines','tools','users','orders','time_bookings','machine_control_states','machine_control_lock',
                  'machine_control_commands','production_plan_entries','order_completions'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    for model in (MachineToolState,SetupOperation):
        if inspector.has_table(model.__tablename__):
            actual={c['name'] for c in inspector.get_columns(model.__tablename__)}
            if not set(model.__table__.columns.keys()).issubset(actual):raise RuntimeError('Unvollständige Tabelle: '+model.__tablename__)
    if check_only:print('Werkzeugbestand/Rüsthistorie: Strukturprüfung erfolgreich. Keine Änderungen.');return
    for model in (MachineToolState,SetupOperation):model.__table__.create(bind=db.engine,checkfirst=True)
    db.session.commit()
    print('Werkzeugbestand und Rüsthistorie eingerichtet. Bestehende Bestände bleiben ungeprüft; keine Altbuchung verändert.')


if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
