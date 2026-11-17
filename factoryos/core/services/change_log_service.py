from flask_login import current_user
from flask import has_request_context
from datetime import date, datetime
from decimal import Decimal
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog


def log_change(entity_type, entity_id, action, changes=None, category=None, entity_name=None):

    log = ChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        action=action,
        changes=changes or {},
        category=category,
        user_id=current_user.id if has_request_context() and current_user.is_authenticated else None
    )

    db.session.add(log)
    return log

def build_changes(old_obj, new_data, fields):
    changes = {}

    for field in fields:
        old_value = getattr(old_obj, field)
        new_value = new_data.get(field)

        if not same_value(old_value,new_value):
            changes[field] = {
                "old": old_value,
                "new": new_value
            }

    return changes

def same_value(old,new):
    if old in (None,'') and new in (None,''):return True
    return old==new or str(old)==str(new)

def snapshot(obj,fields):
    def value(item):
        if isinstance(item,(date,datetime)):return item.isoformat()
        if isinstance(item,Decimal):return str(item)
        return item
    return {key:value(getattr(obj,key)) for key in fields}

def record_entity(obj,entity_type,action,fields,*,before=None,category='administration',entity_name=None):
    """Add an audit record to the caller's transaction; never commit separately."""
    if action=='create':db.session.flush()
    after=snapshot(obj,fields)
    if action=='delete':changes={key:{'old':val,'new':None} for key,val in after.items()}
    elif before is not None:changes={key:{'old':before.get(key),'new':val} for key,val in after.items() if not same_value(before.get(key),val)}
    else:changes={key:{'old':None,'new':val} for key,val in after.items()}
    if action=='update' and not changes:return
    name=entity_name or next((after.get(key) for key in ('username','gauge_no','order_no','name','tool_no','title') if after.get(key)),str(obj.id))
    return log_change(entity_type,obj.id,action,changes=changes,category=category,entity_name=name)
