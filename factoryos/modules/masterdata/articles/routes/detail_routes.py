from flask import render_template, request
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from factoryos.core.queries.change_log_queries import get_logs
from ..queries.sampling_queries import sampling_summaries, article_sampling_page, article_log_page
from factoryos.modules.sampling.definitions import REASONS, STATES, CHECK_STATUSES


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
        sampling_summary=sampling_summaries([article.id])[article.id],
        logs=logs
    )


@bp.route("/<int:article_id>/history")
@login_required
def history(article_id):
    article = get_article(article_id)

    def page_arg(name):
        value = request.args.get(name, 1, type=int)
        return min(1000000, max(1, value or 1))

    response = render_template(
        "masterdata/articles/history.html", article=article,
        samplings=article_sampling_page(article.id, page_arg("sampling_page")),
        history_logs=article_log_page(article.id, page_arg("log_page")),
        summary=sampling_summaries([article.id])[article.id],
        reasons=REASONS, states=STATES, check_statuses=CHECK_STATUSES,
    )
    return response, 200, {"Cache-Control": "private, no-store"}
