from flask import redirect, url_for, flash
from flask_login import login_required

from . import bp
from ..queries.article_queries import get_article
from ..services.article_service import delete_article


@bp.route("/delete/<int:article_id>")
@login_required
def delete(article_id):

    article = get_article(article_id)
    from sqlalchemy import inspect as defect_inspect
    from factoryos.extensions import db as defect_db
    from factoryos.modules.article_defects.models import ArticleDefect
    if defect_inspect(defect_db.engine).has_table('article_defects') and ArticleDefect.query.filter_by(article_id=article.id).first():
        flash('Artikel besitzt Fehlerkatalog-Historie und bleibt zur Nachverfolgung erhalten.','warning')
        return redirect(url_for('articles.detail',article_id=article.id))
    from sqlalchemy import inspect
    from factoryos.extensions import db
    from factoryos.modules.inventory.models import WarehouseLot
    if inspect(db.engine).has_table('warehouse_lots') and WarehouseLot.query.filter_by(article_id=article.id).first():
        flash('Artikel besitzt Lagerhistorie und bleibt zur Rückverfolgung erhalten.','warning')
        return redirect(url_for('articles.detail',article_id=article.id))

    from factoryos.modules.sampling.models import SamplingOrder
    if SamplingOrder.query.filter_by(article_id=article.id).first():
        flash("Dieser Artikel wird von einem Musterungsauftrag verwendet und kann nicht gelöscht werden.", "warning")
        return redirect(url_for("articles.detail", article_id=article.id))
    delete_article(article)

    return redirect(url_for("articles.list"))
