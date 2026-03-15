from datetime import datetime
from factoryos.extensions import db

class Order(db.Model):

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    order_no = db.Column(db.String(50), unique=True, nullable=False, index=True)

    tool_no = db.Column(db.String(50), nullable=True)

    is_project = db.Column(db.Boolean, default=False)

    article = db.Column(db.String(120), nullable=True)

    article_name = db.Column(db.String(255), nullable=True)

    description = db.Column(db.String(255), nullable=True)

    location = db.Column(db.String(100), nullable=True)

    target_qty = db.Column(db.Integer, default=0)

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