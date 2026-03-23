from factoryos.extensions import db

article_tools = db.Table(
    "article_tools",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id"), primary_key=True),
    db.Column("tool_id", db.Integer, db.ForeignKey("tools.id"), primary_key=True)
)
