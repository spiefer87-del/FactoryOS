from factoryos.core.models.change_log import ChangeLog


def get_logs(entity_type=None, entity_id=None, limit=None, action=None, search=None):

    query = ChangeLog.query

    # 🔹 Filter nach Entity
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    if entity_id:
        query = query.filter_by(entity_id=entity_id)

    # 🔹 Filter nach Action
    if action:
        query = query.filter_by(action=action)

    # 🔹 Suche (Name)
    if search:
        query = query.filter(ChangeLog.entity_name.ilike(f"%{search}%"))

    # 🔹 Sortierung
    query = query.order_by(ChangeLog.created_at.desc())

    # 🔹 Limit
    if limit and limit != "all":
        query = query.limit(int(limit))

    return query.all()
