from flask import redirect, url_for, flash
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from ..services.article_service import delete_article


@bp.route("/delete/<int:article_id>")
@login_required
def delete(article_id):

    article = get_article(article_id)

    from factoryos.modules.sampling.models import SamplingOrder
    if SamplingOrder.query.filter_by(article_id=article.id).first():
        flash("Dieser Artikel wird von einem Musterungsauftrag verwendet und kann nicht gelöscht werden.", "warning")
        return redirect(url_for("articles.detail", article_id=article.id))
    delete_article(article)

    return redirect(url_for("articles.list"))
