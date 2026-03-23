from datetime import datetime
from factoryos.extensions import db
from factoryos.modules.masterdata.shared.models.article_tool import article_tools


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation
    tool_no = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)

    # Produktionsdaten
    shot_weight_g = db.Column(db.Float, nullable=True)
    cycle_time_s = db.Column(db.Float, nullable=True)

    cavities = db.Column(db.Integer, nullable=True)
    pack_unit = db.Column(db.Integer, nullable=True)

    location = db.Column(db.String(100), nullable=True, index=True)

    # Status
    tool_status = db.Column(db.String(50), nullable=False, default="OK")

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    # 🔗 Beziehung zu Artikeln (NEU)
    articles = db.relationship(
        "Article",
        secondary=article_tools,
        back_populates="tools"
    )