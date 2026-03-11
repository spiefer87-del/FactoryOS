from extensions import db


class ToolMasterdata(db.Model):

    __tablename__ = "tool_masterdata"

    id = db.Column(db.Integer, primary_key=True)

    tool_no = db.Column(db.String(50), unique=True)

    article_no = db.Column(db.String(50))

    article_name = db.Column(db.String(200))