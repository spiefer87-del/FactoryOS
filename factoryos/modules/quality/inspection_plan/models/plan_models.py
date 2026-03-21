from datetime import datetime
from factoryos.extensions import db

class QualityInspectionPlan(db.Model):
    __tablename__ = "qm_plans"

    id = db.Column(db.Integer, primary_key=True)

    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    tool = db.relationship("Tool")
    created_by = db.relationship("User")

    versions = db.relationship(
        "QualityInspectionPlanVersion",
        backref="plan",
        cascade="all, delete-orphan",
        order_by="QualityInspectionPlanVersion.created_at.desc()"
    )

    change_logs = db.relationship(
        "QualityInspectionChangeLog",
        cascade="all, delete-orphan",
        order_by="QualityInspectionChangeLog.created_at.desc()"
    )

class QualityInspectionPlanVersion(db.Model):
    __tablename__ = "qm_plan_versions"

    id = db.Column(db.Integer, primary_key=True)

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_plans.id", ondelete="CASCADE")
    )

    revision = db.Column(db.String(20), nullable=False)

    status = db.Column(db.String(20), default="draft")  # draft / released

    released_at = db.Column(db.DateTime)
    released_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    pdf_path = db.Column(db.String(300))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    released_by = db.relationship("User")

    sections = db.relationship(
        "QualityInspectionSection",
        backref="version",
        cascade="all, delete-orphan",
        order_by="QualityInspectionSection.sort_order.asc()",
        lazy="selectin"
    )


    is_dirty = db.Column(db.Boolean, default=False)

class QualityInspectionSection(db.Model):
    __tablename__ = "qm_sections"

    id = db.Column(db.Integer, primary_key=True)

    plan_version_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_plan_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    title = db.Column(db.String(200), nullable=False)
    section_type = db.Column(db.String(50), nullable=False)

    sort_order = db.Column(db.Integer, default=0)

    drawing_path = db.Column(db.String(300), nullable=True)

    images = db.relationship(
        "QualityInspectionIdentificationImage",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="QualityInspectionIdentificationImage.uploaded_at.asc()"
    )

    image_width = db.Column(db.Integer)
    image_height = db.Column(db.Integer)

    snippets = db.relationship(
        "QualityInspectionDimensionSnippet",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="QualityInspectionDimensionSnippet.sort_order.asc()"
    )

    characteristics = db.relationship(
        "QualityInspectionCharacteristic",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="QualityInspectionCharacteristic.sort_order.asc()"
    )

    gauge_checks = db.relationship(
        "QualityInspectionGaugeCheck",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="QualityInspectionGaugeCheck.sort_order.asc()"
    )



