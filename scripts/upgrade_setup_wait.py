#!/usr/bin/env python3
"""Add idle evidence only. No historical attribution, booking rewrite or grants."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import BookingIdleContext

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table in ('time_bookings','machine_tool_states','setup_operations','machine_control_commands',
                  'machine_control_states','machine_control_lock','orders','production_plan_entries'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    table=BookingIdleContext.__tablename__
    if inspector.has_table(table) and not set(BookingIdleContext.__table__.columns.keys()).issubset({c['name'] for c in inspector.get_columns(table)}):
        raise RuntimeError('Unvollständige Tabelle: '+table)
    if check_only:print('Rüstende/Wartezeiten: Strukturprüfung erfolgreich.');return
    BookingIdleContext.__table__.create(bind=db.engine,checkfirst=True)
    db.session.commit()
    print('Rüstende und Wartegründe vorbereitet. Keine Altbuchungen, Bestände, Mengen oder Rollenrechte geändert.')

if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
