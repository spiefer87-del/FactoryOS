from datetime import datetime
from factoryos.extensions import db
from factoryos.modules.sampling.models import SamplingOrder
from .import_models import ERPOrderData, ERPImportBatch

class Order(db.Model):

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    sampling = db.relationship("SamplingOrder", back_populates="order", uselist=False)
    erp_import = db.relationship("ERPOrderData", back_populates="order", uselist=False,
                                 cascade="all, delete-orphan")

    order_no = db.Column(db.String(50), unique=True, nullable=False, index=True)

    tool_no = db.Column(db.String(50), nullable=True)

    is_project = db.Column(db.Boolean, default=False)

    article = db.Column(db.String(120), nullable=True)

    article_name = db.Column(db.String(255), nullable=True)

    description = db.Column(db.String(255), nullable=True)

    location = db.Column(db.String(100), nullable=True)

    target_qty = db.Column(db.Integer, default=0)
    # Nullable only for legacy and non-production project orders.
    cycle_time_s = db.Column(db.Float, nullable=True)

    status = db.Column(
        db.String(20),
        default="open",
        index=True
    )  # open, running, finished, locked


    project_leader_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    project_leader = db.relationship(
        "User",
        foreign_keys=[project_leader_id]
    )


    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime,
        default=db.func.now(),
        onupdate=db.func.now()
    )
