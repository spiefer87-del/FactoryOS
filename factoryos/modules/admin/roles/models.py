from factoryos.extensions import db
from factoryos.modules.admin.permissions.models import role_permissions


class Role(db.Model):

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(50), unique=True)

    description = db.Column(db.String(255))

    active = db.Column(db.Boolean, default=True)

    users = db.relationship("User", back_populates="role")

    permissions = db.relationship(
        "Permission",
        secondary=role_permissions,
        backref="roles"
    )