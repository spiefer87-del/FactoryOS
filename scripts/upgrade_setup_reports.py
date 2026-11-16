#!/usr/bin/env python3
"""Add only new report tables/permissions. Existing masters and grants unchanged."""
import sys
from pathlib import Path
from sqlalchemy import inspect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.setup_reports.models import SetupReport,SetupReportRevision,SetupReportPhoto
from factoryos.modules.setup_reports.schema import PERMISSIONS
from factoryos.modules.admin.permissions.models import Permission


def run_upgrade(check_only=False):
    inspector=inspect(db.engine)
    for table in ("tools","articles","materials","machines","users","permissions"):
        if not inspector.has_table(table):raise RuntimeError("Voraussetzung fehlt: "+table)
    for model in (SetupReport,SetupReportRevision,SetupReportPhoto):
        if inspector.has_table(model.__tablename__):
            actual={c["name"] for c in inspector.get_columns(model.__tablename__)}
            if not set(model.__table__.columns.keys()).issubset(actual):raise RuntimeError("Unvollständige Berichtstabelle. Nicht automatisch überschrieben: "+model.__tablename__)
    if check_only:print("Einstellbericht-Strukturprüfung erfolgreich. Keine Änderungen.");return
    for model in (SetupReport,SetupReportRevision,SetupReportPhoto):model.__table__.create(bind=db.engine,checkfirst=True)
    for action,description in PERMISSIONS.items():
        if not Permission.query.filter_by(name="setup_reports."+action).first():db.session.add(Permission(name="setup_reports."+action,description=description))
    db.session.commit()
    print("Einstellbericht-Upgrade erfolgreich. Rechte anderer Rollen unverändert; bitte ausdrücklich vergeben.")


if __name__=="__main__":
    app=create_app()
    with app.app_context():run_upgrade("--check" in sys.argv)
