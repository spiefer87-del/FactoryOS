from datetime import datetime
from factoryos.extensions import db


class SamplingOrder(db.Model):
    __tablename__ = "sampling_orders"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, unique=True)
    reason = db.Column(db.String(30), nullable=False)
    state = db.Column(db.String(30), nullable=False, default="draft")
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"))
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"))
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"))
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"))
    previous_id = db.Column(db.Integer, db.ForeignKey("sampling_orders.id"))
    snapshot = db.Column(db.JSON, nullable=False, default=dict)
    data = db.Column(db.JSON, nullable=False, default=dict)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    order = db.relationship("Order", back_populates="sampling")
    article = db.relationship("Article")
    customer = db.relationship("Customer")
    tool = db.relationship("Tool")
    material = db.relationship("Material")
    machine = db.relationship("Machine")
    previous = db.relationship("SamplingOrder", remote_side=[id])
    checks = db.relationship("SamplingCheck", back_populates="sampling", cascade="all, delete-orphan")
    __mapper_args__ = {"version_id_col": version}


class SamplingCheck(db.Model):
    __tablename__ = "sampling_checks"
    id = db.Column(db.Integer, primary_key=True)
    sampling_id = db.Column(db.Integer, db.ForeignKey("sampling_orders.id"), nullable=False, index=True)
    key = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")
    note = db.Column(db.Text)
    evidence_date = db.Column(db.Date)
    updated_at = db.Column(db.DateTime)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_by = db.relationship("User")
    sampling = db.relationship("SamplingOrder", back_populates="checks")
    __table_args__ = (db.UniqueConstraint("sampling_id", "key", name="uq_sampling_check_key"),)

