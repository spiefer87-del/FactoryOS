from datetime import datetime
from factoryos.extensions import db


class ChangeLog(db.Model):
    __tablename__ = "change_logs"

    id = db.Column(db.Integer, primary_key=True)

    # 🔗 Kontext
    entity_type = db.Column(db.String(50), nullable=False)   # article, tool, qm_plan
    entity_id = db.Column(db.Integer, nullable=False)

    # 🔥 Aktion
    action = db.Column(db.String(50), nullable=False)        # create, update, delete, link, unlink

    # 📊 Änderungen (flexibel!)
    changes = db.Column(db.JSON)

    # 🧩 Kategorie
    category = db.Column(db.String(50))  # masterdata, qm, production

    # 👤 User
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # 🕒 Zeit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
