from factoryos.extensions import db

from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.production.models import Order, DowntimeReason
from factoryos.modules.masterdata.tools.models import ToolErrorTitlePreset


def seed_database():

    # Admin User
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)

    # Maschinen
    if not Machine.query.first():
        db.session.add(Machine(name="Maschine 1", location="Halle A"))
        db.session.add(Machine(name="Maschine 2", location="Halle A"))

    # Test Orders
    if not Order.query.first():
        db.session.add(Order(order_no="A-10001", article="Artikel 1",
                             description="Testauftrag", target_qty=1000))

        db.session.add(Order(order_no="A-10002", article="Artikel 2",
                             description="Testauftrag", target_qty=500))

    # Downtime Gründe
    if not DowntimeReason.query.first():
        db.session.add(DowntimeReason(name="Material fehlt"))
        db.session.add(DowntimeReason(name="Werkzeug defekt"))
        db.session.add(DowntimeReason(name="Warten auf QS"))

    # Tool Error Presets
    if not ToolErrorTitlePreset.query.first():

        presets = [
            "Angußbuchse defekt",
            "Auswerfer defekt",
            "Kühlung defekt",
            "Düse undicht",
            "Werkzeug schließt nicht",
            "Werkzeug öffnet nicht",
            "Gratbildung",
            "Kernzug defekt",
            "Heißkanal defekt",
            "Sensor defekt",
        ]

        for i, t in enumerate(presets, start=1):
            db.session.add(
                ToolErrorTitlePreset(
                    title=t,
                    sort_order=i,
                    active=True
                )
            )

    db.session.commit()
