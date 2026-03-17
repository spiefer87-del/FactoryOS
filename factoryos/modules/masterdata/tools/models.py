from factoryos.extensions import db


class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)

    tool_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_by = db.relationship("User", foreign_keys=[created_by_id])
