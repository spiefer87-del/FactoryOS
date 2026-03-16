from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from ..services.article_service import update_article


@bp.route("/edit/<int:article_id>", methods=["GET","POST"])
@login_required
def edit(article_id):

    article = get_article(article_id)

    if request.method == "POST":

        update_article(article, request.form)

        return redirect(url_for("articles.list"))

    return render_template(
        "masterdata/articles/edit.html",
        article=article
    )
