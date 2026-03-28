from factoryos.extensions import db
from datetime import datetime

from ..models import ToolError

def create_tool_error(form, user_id):

    error = ToolError(
        tool_id=form.get("tool_id"),
        order_id=form.get("order_id"),
        machine_id=form.get("machine_id"),
        error_type=form.get("error_type"),
        description=form.get("description"),
        reported_by_id=user_id,
        created_at=datetime.utcnow()
    )

    db.session.add(error)
    db.session.commit()

    return error

def delete_tool_error(error):

    db.session.delete(error)
    db.session.commit()
