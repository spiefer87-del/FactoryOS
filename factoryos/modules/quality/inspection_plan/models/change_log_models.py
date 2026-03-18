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
