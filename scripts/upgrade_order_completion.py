#!/usr/bin/env python3
"""Add final confirmation table and rights only. Never rewrite existing orders."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import OrderCompletion
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT


def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table in ('orders','users','machines','quantity_reports','time_bookings','machine_control_lock',
                  'machine_control_states','machine_control_commands','production_plan_entries','production_planning_state','permissions','change_logs'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    if inspector.has_table(OrderCompletion.__tablename__):
        columns={c['name'] for c in inspector.get_columns(OrderCompletion.__tablename__)}
        if not set(OrderCompletion.__table__.columns.keys()).issubset(columns):raise RuntimeError('Unvollständige Abschlusstabelle. Keine automatische Reparatur.')
    if check_only:print('Auftragsabschluss: Strukturprüfung erfolgreich, keine Änderungen.');return
    OrderCompletion.__table__.create(bind=db.engine,checkfirst=True)
    for name in ('orders.complete','production.complete_order'):
        if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    db.session.commit()
    print('Auftragsabschluss eingerichtet. Bestehende Aufträge/Buchungen und Rollenrechte bleiben unverändert.')
    print('Neue Rechte für Einrichter und Büro bewusst zuweisen. Administrator hat Zugriff.')


if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
