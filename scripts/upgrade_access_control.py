#!/usr/bin/env python3
"""Add missing permission names only. Never grant new permissions to normal roles."""
import sys
from pathlib import Path
from sqlalchemy import inspect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.core.access_control import policy


def run_upgrade(app, check_only=False):
    inspector=inspect(db.engine)
    for table in ("users","roles","permissions","role_permissions"):
        if not inspector.has_table(table):
            raise RuntimeError("Tabelle fehlt: "+table)
    admins=[role for role in Role.query.all() if (role.name or "").strip().casefold()=="admin"]
    if len(admins)!=1 or not admins[0].active or not User.query.filter_by(role_id=admins[0].id,active=True).first():
        raise RuntimeError("Genau eine aktive Systemrolle admin mit mindestens einem aktiven Benutzer ist erforderlich. Upgrade abgebrochen.")
    names=set()
    for rule in app.url_map.iter_rules():
        spec=policy(rule.endpoint,app.view_functions.get(rule.endpoint))
        if spec=="DENY":
            raise RuntimeError("Keine explizite Rechtezuordnung für "+rule.endpoint)
        if spec and "." in spec:names.add(spec)
    existing={p.name for p in Permission.query.all()}
    missing=sorted(names-existing)
    print("Zusätzliche Rechte:",", ".join(missing) or "keine")
    if check_only:
        print("Prüfung erfolgreich. Bestehende Rollenrechte unverändert.")
        return
    for name in missing:
        db.session.add(Permission(name=name,description=name))
    db.session.commit()
    print("Rechtekatalog aktualisiert. Neue Rechte für Fachrollen im Adminbereich bewusst zuweisen.")


if __name__=="__main__":
    app=create_app()
    with app.app_context():run_upgrade(app,"--check" in sys.argv)
