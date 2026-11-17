#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.article_defects.models import ArticleDefect,ArticleDefectPhoto,InspectionResetRun
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT
MODELS=(ArticleDefect,ArticleDefectPhoto,InspectionResetRun)

def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    if db.engine.dialect.name!='sqlite':raise RuntimeError('Installer erwartet die vorhandene SQLite-Datenbank.')
    for table in ('articles','users','permissions','qm_plans','qm_plan_versions','qm_sections'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    for model in MODELS:
        required=set(model.__table__.columns.keys())-({'tool_no'} if model is ArticleDefect else set())
        if inspector.has_table(model.__tablename__) and not required.issubset({c['name'] for c in inspector.get_columns(model.__tablename__)}):raise RuntimeError('Unvollständige Tabelle: '+model.__tablename__)
    if check_only:print('Fehlerkatalog-Strukturprüfung erfolgreich; keine Änderungen.');return
    for model in MODELS:model.__table__.create(bind=db.engine,checkfirst=True)
    if 'tool_no' not in {c['name'] for c in inspect(db.engine).get_columns('article_defects')}:
        db.session.execute(text('ALTER TABLE article_defects ADD COLUMN tool_no VARCHAR(100)'))
    db.session.execute(text("CREATE TRIGGER IF NOT EXISTS preserve_defect_article BEFORE DELETE ON articles WHEN EXISTS (SELECT 1 FROM article_defects WHERE article_id=OLD.id) BEGIN SELECT RAISE(ABORT,'Artikel besitzt Fehlerkatalog-Historie'); END"))
    for name in ('defects.view','defects.create','defects.edit','defects.delete_photos','complaints.view'):
        if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    db.session.commit();print('Fehlerkatalog und Reklamationskategorie eingerichtet. Keine Fachrollen automatisch berechtigt.')

if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
