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
