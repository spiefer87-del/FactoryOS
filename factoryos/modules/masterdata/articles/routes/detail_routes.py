from flask import render_template, request
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from factoryos.core.queries.change_log_queries import get_logs


@bp.route("/<int:article_id>")
@login_required
def detail(article_id):

    article = get_article(article_id)

    # 🔥 Limit sauber behandeln
    limit_param = request.args.get("limit", "5")

    if limit_param == "all":
        limit = None
    else:
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 5  # fallback

    # 🔥 Logs laden
    logs = get_logs(
        entity_type="article",
        entity_id=article.id,
        limit=limit
    )

    return render_template(
        "masterdata/articles/detail.html",
        article=article,
        logs=logs
    )
