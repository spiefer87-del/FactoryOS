import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT

def run_upgrade():
    name='production.cancel_booking'
    if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    db.session.commit()
    print('Buchungsprüfung eingerichtet; bestehende Rollenrechte unverändert. Kein Datenreset.')

if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade()
