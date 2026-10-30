from flask import render_template, request, redirect, url_for, flash
from factoryos.extensions import db
from factoryos.modules.masterdata.customers.models import Customer
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from ..services.article_service import update_article

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article

@bp.route("/edit/<int:article_id>", methods=["GET","POST"])
@login_required
def edit(article_id):

    article = Article.query.get_or_404(article_id)

    if request.method == "POST":
        try:
            update_article(article, request.form)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return redirect(request.url)
        return redirect(url_for("articles.list"))

    tools = Tool.query.order_by(Tool.tool_no).all()

    return render_template(
        "masterdata/articles/edit.html",
        article=article,
        tools=tools,
        customers=Customer.query.order_by(Customer.name).all()
    )
    

