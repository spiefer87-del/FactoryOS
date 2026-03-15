from factoryos.extensions import db


class Machine(db.Model):

    __tablename__ = "machines"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), unique=True)

    location = db.Column(db.String(120))

    active = db.Column(db.Boolean, default=True)