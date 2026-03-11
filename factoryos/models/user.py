from extensions import db
from flask_login import UserMixin


class User(db.Model, UserMixin):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default="mitarbeiter")

    active = db.Column(db.Boolean, default=True)