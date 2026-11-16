from datetime import datetime
from factoryos.extensions import db


class SetupReport(db.Model):
    __tablename__ = "setup_reports"
    id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"), nullable=False, index=True)
    tool = db.relationship("Tool")
    previous_id = db.Column(db.Integer, db.ForeignKey("setup_reports.id"))
    version = db.Column(db.Integer, nullable=False, default=1)
    state = db.Column(db.String(20), nullable=False, default="draft")
    context = db.Column(db.JSON, nullable=False, default=dict)
    data = db.Column(db.JSON, nullable=False, default=dict)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    released_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    released_at = db.Column(db.DateTime)
    __mapper_args__ = {"version_id_col": version}


class SetupReportRevision(db.Model):
    __tablename__ = "setup_report_revisions"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("setup_reports.id"), nullable=False, index=True)
    version = db.Column(db.Integer, nullable=False)
    snapshot = db.Column(db.JSON, nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("report_id", "version"),)


class SetupReportPhoto(db.Model):
    __tablename__ = "setup_report_photos"
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("setup_reports.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    text = db.Column(db.Text, nullable=False, default="")
    result = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
