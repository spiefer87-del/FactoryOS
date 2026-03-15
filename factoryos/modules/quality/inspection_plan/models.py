from datetime import datetime
from factoryos.extensions import db

class QualityInspectionPlan(db.Model):
    __tablename__ = "qm_plans"

    id = db.Column(db.Integer, primary_key=True)

    tool_id = db.Column(db.Integer, db.ForeignKey("tool_masterdata.id"), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    tool = db.relationship("ToolMasterdata")
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

class QualityInspectionCharacteristic(db.Model):
    __tablename__ = "qm_characteristics"

    id = db.Column(db.Integer, primary_key=True)

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_sections.id"),
        nullable=False,
        index=True
    )

    name = db.Column(db.String(200))

    target_value = db.Column(db.String(50))
    tolerance_minus = db.Column(db.String(50))
    tolerance_plus = db.Column(db.String(50))
    unit = db.Column(db.String(20))

    pos_x = db.Column(db.Float)
    pos_y = db.Column(db.Float)

    # WICHTIG
    sort_order = db.Column(db.Integer, default=0)

    section = db.relationship(
        "QualityInspectionSection",
        back_populates="characteristics"
    )

class QualityInspectionIdentificationImage(db.Model):
    __tablename__ = "qm_section_images"

    id = db.Column(db.Integer, primary_key=True)

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_sections.id"),
        nullable=False
    )

    image_path = db.Column(db.String(300), nullable=False)

    description = db.Column(db.String(300))

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    section = db.relationship(
        "QualityInspectionSection",
        back_populates="images"
    )

class QualityInspectionDimensionSnippet(db.Model):
    __tablename__ = "qm_dimension_snippets"

    id = db.Column(db.Integer, primary_key=True)

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_sections.id"),
        nullable=False
    )

    image_path = db.Column(db.String(300))
    description = db.Column(db.String(300))

    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    section = db.relationship(
        "QualityInspectionSection",
        back_populates="snippets"
    )

class QualityInspectionGaugeCheck(db.Model):

    __tablename__ = "qm_gauge_checks"

    id = db.Column(db.Integer, primary_key=True)

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_sections.id", ondelete="CASCADE"),
        index=True
    )

    gauge_id = db.Column(
        db.Integer,
        db.ForeignKey("gauge.id", ondelete="SET NULL"),
        nullable=True
    )

    name = db.Column(db.String(200))

    method = db.Column(db.String(200))

    sort_order = db.Column(db.Integer, default=0)

    section = db.relationship(
        "QualityInspectionSection",
        back_populates="gauge_checks"
    )

    gauge = db.relationship("Gauge")


class QualityInspectionChangeLog(db.Model):

    __tablename__ = "qm_change_logs"

    id = db.Column(db.Integer, primary_key=True)

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_plans.id", ondelete="CASCADE")
    )

    version_id = db.Column(
        db.Integer,
        db.ForeignKey("qm_plan_versions.id", ondelete="CASCADE")
    )

    action = db.Column(db.String(50))
    message = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User")
    version = db.relationship("QualityInspectionPlanVersion")