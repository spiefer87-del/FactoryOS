from flask import render_template
from flask_login import login_required
from . import bp
from factoryos.modules.masterdata.articles.models import Article


@bp.route("/list")
@login_required
def list_articles():

    articles = Article.query.order_by(Article.article_no).all()

    return render_template(
        "masterdata/articles/list.html",
        articles=articles
    )
