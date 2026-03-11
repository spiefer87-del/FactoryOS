from sqlalchemy import or_


def search_query(query, model, fields, q):

    if not q:
        return query

    like = f"%{q}%"

    filters = []

    for field in fields:
        filters.append(getattr(model, field).ilike(like))

    return query.filter(or_(*filters))