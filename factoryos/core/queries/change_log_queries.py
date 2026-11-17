from factoryos.core.models.change_log import ChangeLog
from flask import has_request_context, request


def get_logs(entity_type=None, entity_id=None, limit=None, action=None, search=None):

    if has_request_context() and request.args.get('limit') in ('5','15','25','50','all'):
        limit=request.args['limit']

    query = ChangeLog.query

    # 🔹 Entity Filter
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    if entity_id:
        query = query.filter_by(entity_id=entity_id)

    # 🔹 Action Filter
    if action:
        query = query.filter_by(action=action)

    # 🔹 Suche (Name)
    if search:
        query = query.filter(ChangeLog.entity_name.ilike(f"%{search}%"))

    # 🔹 Sortierung
    query = query.order_by(ChangeLog.created_at.desc(), ChangeLog.id.desc())

    # 🔹 Limit sauber behandeln
    if limit and limit != "all":
        try:
            limit = int(limit)

            # 🔒 Schutz vor Unsinn
            if limit > 0:
                query = query.limit(limit)

        except (ValueError, TypeError):
            # fallback → kein limit setzen
            pass

    return query.all()
