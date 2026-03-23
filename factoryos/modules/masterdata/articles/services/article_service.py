from factoryos.extensions import db
from ..models import Article

from factoryos.modules.masterdata.tools.models import Tool

def create_article(form):

    tool_ids = form.getlist("tool_ids")

    article = Article(
        article_no=form.get("article_no"),
        article_name=form.get("article_name"),
        description=form.get("description"),
        status=form.get("status")
    )

    # 🔥 Tools verknüpfen
    if tool_ids:
        tools = Tool.query.filter(Tool.id.in_(tool_ids)).all()
        article.tools = tools

    db.session.add(article)
    db.session.commit()

    return article


def update_article(article, form):

    article.article_no = form.get("article_no")
    article.article_name = form.get("article_name")
    article.description = form.get("description")
    article.status = form.get("status")

    db.session.commit()

    return article


def delete_article(article):

    db.session.delete(article)
    db.session.commit()
