from factoryos.extensions import db


class QualityInspectionCheck(db.Model):
    __tablename__ = 'qm_checks'
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('qm_sections.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    requirement = db.Column(db.Text, nullable=False)
    method = db.Column(db.String(300), nullable=False)
    target_value = db.Column(db.String(50))
    tolerance_minus = db.Column(db.String(50))
    tolerance_plus = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    sort_order = db.Column(db.Integer, nullable=False, default=1)
    section = db.relationship('QualityInspectionSection', back_populates='checks')
