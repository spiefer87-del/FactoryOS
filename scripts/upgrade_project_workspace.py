#!/usr/bin/env python3
"""Additive migration only. Existing machine times and warehouse remain unchanged."""
import sys,sqlite3
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from factoryos.extensions import db
from factoryos.modules.projects.workspace_models import MODELS,Workspace,Member,WriteLock
from factoryos.modules.orders.models import Order
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT

PERMISSIONS=('projects.view','projects.create','projects.view_all','projects.work','projects.manage','projects.correct_times')

def run_upgrade(check_only=False,backup=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name!='sqlite':raise RuntimeError('Diese Migration erwartet SQLite.')
    for name in ('orders','users','permissions','tools','time_bookings','sampling_orders','tool_errors'):
        if not inspector.has_table(name):raise RuntimeError('Voraussetzung fehlt: '+name)
    for model in MODELS:
        if inspector.has_table(model.__tablename__) and not set(model.__table__.columns.keys()).issubset({c['name'] for c in inspector.get_columns(model.__tablename__)}):raise RuntimeError('Unvollständige Struktur: '+model.__tablename__)
    if check_only:print('Projektstruktur geprüft. Keine Datenänderung.');return
    if backup:
        database=db.engine.url.database
        if not database or database==':memory:':raise RuntimeError('Keine dateibasierte Datenbank für Sicherung.')
        folder=Path(database).resolve().parent/'backups';folder.mkdir(exist_ok=True)
        target=folder/('before_project_workspace_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
        db.session.rollback()
        raw=db.engine.raw_connection()
        try:
            with sqlite3.connect(target) as connection:raw.driver_connection.backup(connection)
        finally:raw.close()
        target.chmod(0o600);print('Sicherung:',target)
    for model in MODELS:model.__table__.create(bind=db.engine,checkfirst=True)
    for item in Order.query.filter_by(is_project=True):
        if not db.session.get(Workspace,item.id):db.session.add(Workspace(order_id=item.id))
        if item.project_leader_id and not db.session.get(Member,(item.id,item.project_leader_id)):db.session.add(Member(project_id=item.id,user_id=item.project_leader_id))
    if not db.session.get(WriteLock,1):db.session.add(WriteLock(id=1))
    for name in PERMISSIONS:
        if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    for name,table,column,target in (
        ('preserve_project_workspace','orders','order_id','project_workspaces'),
        ('preserve_project_sampling','sampling_orders','sampling_id','project_links'),
        ('preserve_project_error','tool_errors','error_id','project_links'),
        ('preserve_project_tool','tools','tool_id','project_tool_part_events'),
    ):
        db.session.execute(text(f"CREATE TRIGGER IF NOT EXISTS {name} BEFORE DELETE ON {table} WHEN EXISTS (SELECT 1 FROM {target} WHERE {column}=OLD.id) BEGIN SELECT RAISE(ABORT,'Projekt-Historie vorhanden: archivieren statt loeschen'); END"))
    db.session.commit()
    print('Projektbereich ergänzt. Keine Zeiten, Lagerbestände oder Werkzeugzustände verändert. Fachrollen gezielt berechtigen.')

if __name__=='__main__':
    from factoryos import create_app
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv,'--backup' in sys.argv)
