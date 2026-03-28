from flask import render_template, request
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from factoryos.core.queries.change_log_queries import get_logs


@bp.route("/<int:article_id>")
@login_required
def detail(article_id):

    article = get_article(article_id)
    logs = get_logs(
        entity_type="article",
        entity_id=article.id,
        limit=request.args.get("limit", 5)
    )

    return render_template(
        "masterdata/articles/detail.html",
        article=article,
        logs=logs
    )
