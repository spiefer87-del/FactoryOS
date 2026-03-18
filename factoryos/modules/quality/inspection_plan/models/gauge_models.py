from datetime import datetime
from factoryos.extensions import db

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

