"""Read-only article/sampling links; use stable IDs, never article-number guesses."""
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload
from factoryos.extensions import db
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.core.models.change_log import ChangeLog


def sampling_summaries(article_ids):
    ids = set(article_ids)
    if not ids:
        return {}
    summaries = {key: {"open_count": 0, "total": 0, "by_state": {}} for key in ids}
    rows = (db.session.query(SamplingOrder.article_id, SamplingOrder.state, func.count(SamplingOrder.id))
            .filter(SamplingOrder.article_id.in_(ids))
            .group_by(SamplingOrder.article_id, SamplingOrder.state).all())
    for article_id, state, count in rows:
        summary = summaries[article_id]
        summary["total"] += count
        summary["by_state"][state] = count
        if state != "completed":
            summary["open_count"] += count
    return summaries


def article_sampling_page(article_id, page=1):
    return (SamplingOrder.query.filter_by(article_id=article_id)
            .options(joinedload(SamplingOrder.order), selectinload(SamplingOrder.checks))
            .order_by(SamplingOrder.created_at.desc(), SamplingOrder.id.desc())
            .paginate(page=page, per_page=20, error_out=False))


def article_log_page(article_id, page=1):
    return (ChangeLog.query.filter_by(entity_type="article", entity_id=article_id)
            .options(joinedload(ChangeLog.user))
            .order_by(ChangeLog.created_at.desc(), ChangeLog.id.desc())
            .paginate(page=page, per_page=20, error_out=False))
