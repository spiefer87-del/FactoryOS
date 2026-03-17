from factoryos.extensions import db

from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.production.models import DowntimeReason
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import ToolErrorTitlePreset

from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission


# ---------------------------------------------------
# Roles
# ---------------------------------------------------

def seed_roles():

    roles = [
        ("admin", "System Administrator"),
        ("production", "Production User"),
        ("quality", "Quality User")
    ]

    for name, desc in roles:

        existing = Role.query.filter_by(name=name).first()

        if not existing:

            role = Role(
                name=name,
                description=desc,
                active=True
            )

            db.session.add(role)

    db.session.commit()


# ---------------------------------------------------
# Permissions
# ---------------------------------------------------

def seed_permissions():

    permissions = [

        "users.view",
        "users.create",
        "users.edit",
        "users.delete",

        "tools.view",
        "tools.create",
        "tools.edit",
        "tools.delete",

        "production.start",
        "production.stop",

        "quality.inspect"
    ]

    for p in permissions:

        existing = Permission.query.filter_by(name=p).first()

        if not existing:
            db.session.add(Permission(name=p))

    db.session.commit()


# ---------------------------------------------------
# Users
# ---------------------------------------------------

def seed_users():

    if not User.query.filter_by(username="admin").first():

        admin_role = Role.query.filter_by(name="admin").first()

        admin = User(
            username="admin",
            role_id=admin_role.id,
            active=True
        )

        admin.set_password("admin123")

        db.session.add(admin)

    db.session.commit()


# ---------------------------------------------------
# Database Base Data
# ---------------------------------------------------

def seed_database():

    # Maschinen
    if not Machine.query.first():

        db.session.add(Machine(name="Maschine 1", location="Halle A"))
        db.session.add(Machine(name="Maschine 2", location="Halle A"))

    # Test Orders
    if not Order.query.first():

        db.session.add(Order(
            order_no="A-10001",
            article="Artikel 1",
            description="Testauftrag",
            target_qty=1000
        ))

        db.session.add(Order(
            order_no="A-10002",
            article="Artikel 2",
            description="Testauftrag",
            target_qty=500
        ))

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
            "Sensor defekt"

        ]

        for i, title in enumerate(presets, start=1):

            db.session.add(

                ToolErrorTitlePreset(
                    title=title,
                    sort_order=i,
                    active=True
                )

            )

    db.session.commit()


# ---------------------------------------------------
# Master Seed
# ---------------------------------------------------

def run_seeds():

    seed_roles()
    seed_permissions()
    seed_users()
    seed_database()

    print("FactoryOS Seeds geladen")
