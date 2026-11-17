#!/usr/bin/env python3
"""Additive SQLite upgrade, no inferred historical stock and no role grants."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.inventory.models import WarehouseLocation,WarehouseLot,WarehouseReservation,WarehouseEvent,WarehouseLine,WarehouseLock
from factoryos.modules.inventory.service import PERMISSIONS
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT
MODELS=(WarehouseLocation,WarehouseLot,WarehouseReservation,WarehouseEvent,WarehouseLine,WarehouseLock)

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name!='sqlite':raise RuntimeError('Dieser Installer ist für die bestehende SQLite-Installation vorgesehen.')
    for table in ('orders','articles','users','permissions','order_completions','quantity_reports','machine_control_lock'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    for model in MODELS:
        if inspector.has_table(model.__tablename__) and not set(model.__table__.columns.keys()).issubset({c['name'] for c in inspector.get_columns(model.__tablename__)}):raise RuntimeError('Unvollständige Lagertabelle: '+model.__tablename__)
    if check_only:print('Lager-Strukturprüfung erfolgreich. Keine Änderungen.');return
    for model in MODELS:model.__table__.create(bind=db.engine,checkfirst=True)
    for table in ('warehouse_events','warehouse_lines','warehouse_lots'):
        for operation in ('UPDATE','DELETE'):
            db.session.execute(text(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, 'Lagerjournal unveraenderlich'); END"))
    for parent,column in (('orders','order_id'),('articles','article_id')):
        db.session.execute(text(f"CREATE TRIGGER IF NOT EXISTS warehouse_protect_{parent} BEFORE DELETE ON {parent} WHEN EXISTS (SELECT 1 FROM warehouse_lots WHERE {column}=OLD.id) BEGIN SELECT RAISE(ABORT, 'Lagerreferenz vorhanden'); END"))
    for operation in ('UPDATE','DELETE'):
        db.session.execute(text(f"CREATE TRIGGER IF NOT EXISTS warehouse_protect_reports_{operation.lower()} BEFORE {operation} ON quantity_reports WHEN EXISTS (SELECT 1 FROM warehouse_lots WHERE order_id=OLD.order_id) BEGIN SELECT RAISE(ABORT, 'Produktionsmeldung bereits an Lager uebergeben'); END"))
    for name in set(PERMISSIONS.values())|{'inventory.view'}:
        if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    db.session.commit();print('Lager eingerichtet. Keine historischen Mengen eingebucht, keine Fachrollen automatisch berechtigt.')

if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
