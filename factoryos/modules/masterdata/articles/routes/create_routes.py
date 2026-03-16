from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.article_service import create_article


@bp.route("/create", methods=["GET","POST"])
@login_required
def create():

    if request.method == "POST":

        create_article(request.form)

        return redirect(url_for("articles.list"))

    return render_template(
        "masterdata/articles/create.html"
    )
