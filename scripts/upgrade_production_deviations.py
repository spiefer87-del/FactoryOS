import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production_deviations.models import ProductionDeviationConfirmation as Confirmation
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.admin.permissions.labels import PERMISSION_TEXT

def run_upgrade():
    Confirmation.__table__.create(bind=db.engine,checkfirst=True)
    db.session.execute(text("CREATE TRIGGER IF NOT EXISTS preserve_deviation_order BEFORE DELETE ON orders WHEN EXISTS (SELECT 1 FROM production_deviation_confirmations WHERE order_id=OLD.id) BEGIN SELECT RAISE(ABORT,'Auftrag besitzt bestaetigte Laufzeitabweichungen'); END"))
    name='production.confirm_deviation'
    if not Permission.query.filter_by(name=name).first():db.session.add(Permission(name=name,description=PERMISSION_TEXT[name]['description']))
    db.session.commit();print('Laufzeitabweichungen eingerichtet. Keine Maschinenparameter oder Fachrollen geändert.')

if __name__=='__main__':
    app=create_app()
    with app.app_context():run_upgrade()
