from flask import render_template, request
from flask_login import login_required

from . import bp
from ..queries.article_queries import search_articles
from ..queries.sampling_queries import sampling_summaries
from factoryos.modules.sampling.definitions import STATES


@bp.route("/list")
@login_required
def list():

    search = request.args.get("search")

    articles = search_articles(search)

    return render_template(
        "masterdata/articles/list.html",
        articles=articles,
        sampling_summaries=sampling_summaries(a.id for a in articles),
        sampling_states=STATES,
    )
