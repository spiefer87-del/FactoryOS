#!/usr/bin/env python3
"""Additive, repeatable upgrade. No existing plans/releases are rewritten."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect, text
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.quality.inspection_plan.models import QualityInspectionSection, QualityInspectionCheck


def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table in ('qm_plans','qm_plan_versions','qm_sections','qm_characteristics','qm_gauge_checks','qm_change_logs','qm_section_images','qm_dimension_snippets','gauge'):
        if not inspector.has_table(table):raise RuntimeError('Voraussetzung fehlt: '+table)
    columns={c['name'] for c in inspector.get_columns('qm_sections')}
    required=set(QualityInspectionSection.__table__.columns.keys())-{'inspection_settings'}
    if not required.issubset(columns):raise RuntimeError('Bestehende Modultabelle ist unvollständig.')
    if inspector.has_table('qm_checks') and not set(QualityInspectionCheck.__table__.columns.keys()).issubset({c['name'] for c in inspector.get_columns('qm_checks')}):
        raise RuntimeError('Prüfmerkmal-Tabelle ist unvollständig.')
    if db.engine.dialect.name!='sqlite':raise RuntimeError('Dieser Installer ist für die bestehende SQLite-Installation vorgesehen.')
    if check_only:print('Prüfplan: Strukturprüfung erfolgreich; keine Änderungen.');return
    if 'inspection_settings' not in columns:db.session.execute(text('ALTER TABLE qm_sections ADD COLUMN inspection_settings JSON'))
    db.session.commit()
    QualityInspectionCheck.__table__.create(bind=db.engine,checkfirst=True)
    print('Prüfplan-Module eingerichtet. Bestehende Inhalte, Revisionen, Status und Rechte unverändert.')


if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade('--check' in sys.argv)
