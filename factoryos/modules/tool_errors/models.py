from datetime import datetime
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool

class ToolError(db.Model):

    __tablename__ = "tool_errors"

    id = db.Column(db.Integer, primary_key=True)

    error_no = db.Column(db.String(20), unique=True)

    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"), nullable=False)

    error_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reported_by = db.relationship("User")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workflow_status = db.Column(
        db.String(20),
        default="draft"
    )
    
    released_at = db.Column(db.DateTime)
    
    released_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )
    
    released_by = db.relationship(
        "User",
        foreign_keys=[released_by_id]
    )

    revision = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )
    
    parent_error_id = db.Column(
        db.Integer,
        db.ForeignKey("tool_errors.id")
    )
    
    is_current = db.Column(
        db.Boolean,
        default=True
    )
    
    order_id = db.Column(db.Integer)
    machine_id = db.Column(db.Integer)

    tool = db.relationship("Tool", backref="errors")
    
    images = db.relationship(
        "ToolErrorImage",
        backref="tool_error",
        cascade="all, delete-orphan"
    )

class ToolErrorImage(db.Model):

    __tablename__ = "tool_error_images"

    id = db.Column(db.Integer, primary_key=True)

    tool_error_id = db.Column(
        db.Integer,
        db.ForeignKey("tool_errors.id"),
        nullable=True
    )

    image_path = db.Column(db.String(255))

    description = db.Column(db.Text)

    marker_x = db.Column(db.Float)  # Prozent
    marker_y = db.Column(db.Float)

    marker_px = db.Column(db.Integer)  # Pixel
    marker_py = db.Column(db.Integer)

    temp_id = db.Column(db.String, nullable=True)  # 🔥 NEU


class ToolErrorTitlePreset(db.Model):
    __tablename__ = "tool_error_title_presets"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
