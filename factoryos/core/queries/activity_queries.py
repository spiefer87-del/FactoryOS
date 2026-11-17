"""Chronological activity feed using each area's original records."""
from datetime import datetime

from sqlalchemy import inspect, or_
from sqlalchemy.orm import joinedload

from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.orders.models import Order
from factoryos.modules.projects.workspace_models import Audit, Member
from factoryos.modules.projects.services.workspace_service import permitted, mine_clause
from factoryos.modules.projects.services.activity_service import present_audits

ENTITY_LABELS = {
    'project': 'Projekte', 'article': 'Artikel', 'tool': 'Werkzeuge',
    'machine': 'Maschinen', 'material': 'Materialien', 'tool_error': 'Fehlermeldungen',
    'order': 'Aufträge', 'sampling': 'Musterungen', 'customer': 'Kunden',
    'masterbatch': 'Masterbatches', 'qm_plan': 'Prüfpläne',
}
LIMITS = ('5', '15', '25', '50', 'all')


def activity_feed(entity_type=None, limit='50'):
    limit = limit if limit in LIMITS else '50'
    count = None if limit == 'all' else int(limit)
    visible_projects = None
    inspector = inspect(db.engine)
    if permitted('view') and inspector.has_table(Audit.__tablename__) and inspector.has_table(Member.__tablename__):
        visible_projects = Order.query.filter(Order.is_project.is_(True))
        if not permitted('view_all'):
            visible_projects = visible_projects.filter(mine_clause())
    visible_ids = db.select(visible_projects.subquery().c.id) if visible_projects is not None else None

    ordinary = ChangeLog.query.options(joinedload(ChangeLog.user))
    # Respect project visibility if a previous extension wrote generic project logs.
    if visible_ids is None:
        ordinary = ordinary.filter(ChangeLog.entity_type != 'project')
    else:
        ordinary = ordinary.filter(or_(ChangeLog.entity_type != 'project', ChangeLog.entity_id.in_(visible_ids)))
    available = [row[0] for row in ordinary.with_entities(ChangeLog.entity_type).distinct().all()]
    if visible_ids is not None:
        available.append('project')
    if entity_type:
        ordinary = ordinary.filter(ChangeLog.entity_type == entity_type)
    ordinary = ordinary.order_by(ChangeLog.created_at.desc(), ChangeLog.id.desc())
    logs = ordinary.limit(count).all() if count else ordinary.all()

    if visible_ids is not None and entity_type in (None, '', 'project'):
        project_query = Audit.query.filter(Audit.project_id.in_(visible_ids)).order_by(Audit.created_at.desc(), Audit.id.desc())
        project_rows = project_query.limit(count).all() if count else project_query.all()
        logs.extend(present_audits(project_rows))
    logs.sort(key=lambda row: (row.created_at or datetime.min, row.entity_type, row.id), reverse=True)
    if count:
        logs = logs[:count]
    types = {key: ENTITY_LABELS.get(key, key.replace('_', ' ').capitalize()) for key in sorted(set(available))}
    return logs, types, limit
