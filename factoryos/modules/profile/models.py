from datetime import datetime
from factoryos.extensions import db


class UserPreference(db.Model):
    __tablename__ = "user_preferences"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    section = db.Column(db.String(50), primary_key=True)
    values = db.Column(db.JSON, nullable=False, default=dict)
    version = db.Column(db.Integer, nullable=False, default=1)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __mapper_args__ = {"version_id_col": version}
