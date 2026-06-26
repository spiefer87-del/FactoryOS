from datetime import datetime

from factoryos.extensions import db

from factoryos.modules.tool_errors.models import (
    ToolError,
    ToolErrorImage
)


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

    error.released_at = None

    error.released_by_id = None

    db.session.commit()

    return error


# =====================================================
# AKTUELLE REVISION
# =====================================================

def get_current_revision(error):

    if error.is_current:
        return error

    parent_id = error.parent_error_id or error.id

    current = ToolError.query.filter_by(
        parent_error_id=parent_id,
        is_current=True
    ).first()

    return current or error


# =====================================================
# ALLE REVISIONEN
# =====================================================

def get_revisions(error):

    parent_id = error.parent_error_id or error.id

    revisions = ToolError.query.filter(
        (ToolError.id == parent_id) |
        (ToolError.parent_error_id == parent_id)
    ).order_by(
        ToolError.revision.desc()
    ).all()

    return revisions


# =====================================================
# NEUE REVISION
# =====================================================

def create_revision(error, user_id):

    current = get_current_revision(error)

    parent_id = current.parent_error_id or current.id

    current.is_current = False

    next_revision = current.revision + 1

    revision = ToolError(

        error_no=current.error_no,

        tool_id=current.tool_id,

        error_type=current.error_type,

        description=current.description,

        reported_by_id=current.reported_by_id,

        order_id=current.order_id,

        machine_id=current.machine_id,

        workflow_status="draft",

        released_at=None,

        released_by_id=None,

        revision=next_revision,

        parent_error_id=parent_id,

        is_current=True,

        created_at=datetime.utcnow()

    )

    db.session.add(revision)

    db.session.flush()

    # ==========================================
    # BILDER ÜBERNEHMEN
    # ==========================================

    for image in current.images:

        db.session.add(

            ToolErrorImage(

                tool_error_id=revision.id,

                image_path=image.image_path,

                description=image.description,

                marker_x=image.marker_x,

                marker_y=image.marker_y,

                marker_px=image.marker_px,

                marker_py=image.marker_py

            )

        )

    db.session.commit()

    return revision
