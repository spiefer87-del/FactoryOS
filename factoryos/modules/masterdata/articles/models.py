from factoryos.extensions import db
from .article_tool import article_tools


class Article(db.Model):

    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    article_no = db.Column(db.String(50), unique=True, nullable=False)

    article_name = db.Column(db.String(200), nullable=False)

    description = db.Column(db.Text)

    status = db.Column(db.String(20), default="active")
        tools = db.relationship(
        "Tool",
        secondary=article_tools,
        back_populates="articles"
        )
