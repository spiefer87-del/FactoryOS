from datetime import datetime

from factoryos.extensions import db
from factoryos.modules.tool_errors.models import ToolError


# =====================================================
# IN PRÜFUNG
# =====================================================

def start_review(error):

    error.workflow_status = "review"

    db.session.commit()

    return error


# =====================================================
# FREIGEBEN
# =====================================================

def release(error, user):

    error.workflow_status = "released"

    error.released_at = datetime.utcnow()

    error.released_by_id = user.id

    db.session.commit()

    return error


# =====================================================
# SCHLIESSEN
# =====================================================

def close(error):

    error.workflow_status = "closed"

    db.session.commit()

    return error


# =====================================================
# WIEDER ÖFFNEN
# =====================================================

def reopen(error):

    error.workflow_status = "draft"

    db.session.commit()

    return error


# =====================================================
# AKTUELLE REVISION
# =====================================================

def get_current_revision(error):

    if error.is_current:
        return error

    return ToolError.query.filter_by(
        parent_error_id=error.parent_error_id,
        is_current=True
    ).first()
