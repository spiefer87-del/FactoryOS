from flask import render_template
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article, get_article_logs


@bp.route("/<int:article_id>")
@login_required
def detail(article_id):

    article = get_article(article_id)
    logs = get_article_logs(article.id)  # 🔥 jetzt aus Query

    return render_template(
        "masterdata/articles/detail.html",
        article=article,
        logs=logs
    )
