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

    db.session.commit()

    return error


# =====================================================
# AKTUELLE REVISION
# =====================================================

def get_current_revision(error):

    if error.is_current:
        return error

    parent_id = error.parent_error_id or error.id

    return ToolError.query.filter_by(
        parent_error_id=parent_id,
        is_current=True
    ).first()


# =====================================================
# NEUE REVISION
# =====================================================

def create_revision(error):

    # Stammrevision bestimmen
    parent_id = error.parent_error_id or error.id

    current = get_current_revision(error)

    if current:
        current.is_current = False

    revision = ToolError(

        error_no=error.error_no,

        tool_id=error.tool_id,

        error_type=error.error_type,

        description=error.description,

        reported_by_id=error.reported_by_id,

        order_id=error.order_id,

        machine_id=error.machine_id,

        workflow_status="draft",

        revision=(current.revision + 1) if current else 2,

        parent_error_id=parent_id,

        is_current=True,

        created_at=datetime.utcnow()
    )

    db.session.add(revision)

    db.session.flush()

    # ==========================================
    # BILDER ÜBERNEHMEN
    # ==========================================

    for image in error.images:

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
