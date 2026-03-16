from factoryos.extensions import db
from ..models import Article


def create_article(form):

    article = Article(
        article_no=form.get("article_no"),
        article_name=form.get("article_name"),
        description=form.get("description"),
        status=form.get("status")
    )

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
