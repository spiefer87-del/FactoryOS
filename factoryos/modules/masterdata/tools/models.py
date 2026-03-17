from factoryos.extensions import db

class ToolError(db.Model):

    __tablename__ = "tool_errors"

    id = db.Column(db.Integer, primary_key=True)

    tool_id = db.Column(db.Integer, db.ForeignKey("tools.id"))
    order_id = db.Column(db.Integer)

    machine_id = db.Column(db.Integer)

    error_type = db.Column(db.String(100))

    description = db.Column(db.Text)

    reported_by = db.Column(db.Integer)

    created_at = db.Column(db.DateTime)
