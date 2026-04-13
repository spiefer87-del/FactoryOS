from datetime import datetime
from factoryos.extensions import db
from factoryos.modules.masterdata.shared.models.article_tool import article_tools


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation
    tool_no = db.Column(db.String(100), unique=True, nullable=False)
    external_tool_no = db.Column(db.String(100))

    name = db.Column(db.String(100))
    description = db.Column(db.Text)

    # 🔧 Werkzeugdaten
    built_by = db.Column(db.String(150))
    build_year = db.Column(db.Integer)
    shot_counter = db.Column(db.Integer)
    last_service_at = db.Column(db.DateTime)
    
    cavities = db.Column(db.Integer)

    tool_weight_kg = db.Column(db.Float)
    tool_length_mm = db.Column(db.Float)
    tool_width_mm = db.Column(db.Float)
    tool_height_mm = db.Column(db.Float)

    centering_type = db.Column(db.String(50))  # z.B. HASCO, Eigenbau
    centering_nozzle_side = db.Column(db.String(100))
    centering_ejector_side = db.Column(db.String(100))

    ejector_connection = db.Column(db.String(50))
    demolding_type = db.Column(db.String(100))
    hotrunner_zones = db.Column(db.Integer)
    automation_type = db.Column(db.String(50))
    has_conversion_kit = db.Column(db.Boolean, default=False)
    core_pulls = db.Column(db.Integer)

    location = db.Column(db.String(100))

    tool_status = db.Column(db.String(50), default="OK")

    created_at = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User")

    articles = db.relationship(
        "Article",
        secondary=article_tools,
        back_populates="tools"
    )

    images = db.relationship(
        "ToolImage",
        backref="tool",
        cascade="all, delete-orphan"
    )

class ToolImage(db.Model):
    __tablename__ = "tool_images"

    id = db.Column(db.Integer, primary_key=True)

    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"))

    image_path = db.Column(db.String(255))

    title = db.Column(db.String(100))
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
