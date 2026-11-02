"""ERP review drafts and source snapshots. Existing order columns stay unchanged."""
from datetime import datetime
from factoryos.extensions import db


class ERPImportBatch(db.Model):
    __tablename__ = "erp_order_import_batches"
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    sheet = db.Column(db.String(100), nullable=False)
    rows = db.Column(db.JSON, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ERPOrderData(db.Model):
    __tablename__ = "erp_order_data"
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), primary_key=True)
    order = db.relationship("Order", back_populates="erp_import")
    snapshot = db.Column(db.JSON, nullable=False)
    imported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    imported_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
