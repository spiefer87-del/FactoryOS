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
