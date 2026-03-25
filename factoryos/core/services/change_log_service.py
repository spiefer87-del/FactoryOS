from flask_login import current_user
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog


def log_change(entity_type, entity_id, action, changes=None, category=None):

    log = ChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=changes or {},
        category=category,
        user_id=current_user.id if current_user.is_authenticated else None
    )

    db.session.add(log)
