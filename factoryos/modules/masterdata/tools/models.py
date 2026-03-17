from factoryos.extensions import db

class Tool(db.Model):

    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)
    tool_no = db.Column(db.String(50))
    article_no = db.Column(db.String(50))
    article_name = db.Column(db.String(100))
