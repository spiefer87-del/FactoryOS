from flask import render_template, request
from flask_login import login_required

from . import bp
from ..queries.article_queries import search_articles


@bp.route("/list")
@login_required
def list():

    search = request.args.get("search")

    articles = search_articles(search)

    return render_template(
        "masterdata/articles/list.html",
        articles=articles
    )
