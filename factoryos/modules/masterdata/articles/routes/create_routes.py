from flask import render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.article_service import create_article

from factoryos.modules.masterdata.tools.models import Tool

@bp.route("/create", methods=["GET","POST"])
@login_required
def create():

    tools = Tool.query.order_by(Tool.tool_no).all()

    if request.method == "POST":
        create_article(request.form)
        return redirect(url_for("articles.list"))

    return render_template(
        "masterdata/articles/create.html",
        tools=tools
    )
