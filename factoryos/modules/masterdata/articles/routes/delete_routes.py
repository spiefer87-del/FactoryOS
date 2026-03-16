from flask import redirect, url_for
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from ..services.article_service import delete_article


@bp.route("/delete/<int:article_id>")
@login_required
def delete(article_id):

    article = get_article(article_id)

    delete_article(article)

    return redirect(url_for("articles.list"))
