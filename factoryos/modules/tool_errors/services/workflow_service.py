import os
import uuid
import shutil
from datetime import datetime

from flask import current_app
from sqlalchemy import or_

from factoryos.extensions import db
from factoryos.modules.tool_errors.models import ToolError, ToolErrorImage


# =========================
# WORKFLOW STATUS
# =========================

STATUS_DRAFT = "draft"
STATUS_REVIEW = "review"
STATUS_RELEASED = "released"
STATUS_CLOSED = "closed"


# =========================
# WORKFLOW REGELN
# =========================

def can_edit(error):

    return (
        error
        and error.is_current
        and error.workflow_status == STATUS_DRAFT
    )


def ensure_editable(error):

    if not can_edit(error):
        raise PermissionError(
            "Diese Fehlermeldung ist gesperrt und kann nicht bearbeitet werden."
        )


def can_start_review(error):

    return can_edit(error)


def can_release(error):

    return (
        error
        and error.is_current
        and error.workflow_status == STATUS_REVIEW
    )


def can_return_to_draft(error):

    return (
        error
        and error.is_current
        and error.workflow_status == STATUS_REVIEW
    )


def can_close(error):

    return (
        error
        and error.is_current
        and error.workflow_status == STATUS_RELEASED
    )


def can_create_revision(error):

    return (
        error
        and error.is_current
        and error.workflow_status in [
            STATUS_RELEASED,
            STATUS_CLOSED
        ]
    )


# =========================
# REVISIONEN
# =========================

def _revision_root_id(error):

    return error.parent_error_id or error.id


def get_revisions(error):

    root_id = _revision_root_id(error)

    return (
        ToolError.query
        .filter(
            or_(
                ToolError.id == root_id,
                ToolError.parent_error_id == root_id
            )
        )
        .order_by(
            ToolError.revision.asc(),
            ToolError.id.asc()
        )
        .all()
    )


def get_current_revision(error):

    root_id = _revision_root_id(error)

    current = (
        ToolError.query
        .filter(
            or_(
                ToolError.id == root_id,
                ToolError.parent_error_id == root_id
            ),
            ToolError.is_current.is_(True)
        )
        .order_by(
            ToolError.revision.desc(),
            ToolError.id.desc()
        )
        .first()
    )

    if current:
        return current

    return (
        ToolError.query
        .filter(
            or_(
                ToolError.id == root_id,
                ToolError.parent_error_id == root_id
            )
        )
        .order_by(
            ToolError.revision.desc(),
            ToolError.id.desc()
        )
        .first()
    )


def _next_revision_number(error):

    revisions = get_revisions(error)

    max_revision = 0

    for revision in revisions:

        try:
            revision_no = int(revision.revision or 0)
        except Exception:
            revision_no = 0

        if revision_no > max_revision:
            max_revision = revision_no

    return max_revision + 1


def _copy_image_file(image_path):

    if not image_path:
        return None

    source_path = os.path.join(
        current_app.static_folder,
        image_path
    )

    if not os.path.exists(source_path):
        return image_path

    ext = os.path.splitext(source_path)[1]

    if not ext:
        ext = ".jpg"

    filename = f"{uuid.uuid4()}{ext}"

    relative_path = os.path.join(
        "uploads",
        "tool_errors",
        filename
    ).replace("\\", "/")

    target_path = os.path.join(
        current_app.static_folder,
        relative_path
    )

    os.makedirs(
        os.path.dirname(target_path),
        exist_ok=True
    )

    shutil.copy2(
        source_path,
        target_path
    )

    return relative_path


def create_revision(error, user_id):

    current = get_current_revision(error)

    if not can_create_revision(current):
        raise PermissionError(
            "Eine neue Revision kann nur aus einer freigegebenen oder geschlossenen Version erstellt werden."
        )

    root_id = _revision_root_id(current)

    current.is_current = False

    new_revision = ToolError(
        error_no=current.error_no,

        tool_id=current.tool_id,
        order_id=current.order_id,
        machine_id=current.machine_id,
        error_type=current.error_type,
        description=current.description,

        reported_by_id=user_id,
        created_at=datetime.utcnow(),

        workflow_status=STATUS_DRAFT,
        released_at=None,
        released_by_id=None,

        revision=_next_revision_number(current),
        parent_error_id=root_id,
        is_current=True
    )

    db.session.add(new_revision)
    db.session.flush()

    for image in current.images:

        copied_path = _copy_image_file(image.image_path)

        new_image = ToolErrorImage(
            tool_error_id=new_revision.id,
            temp_id=None,

            image_path=copied_path,
            description=image.description,

            marker_x=image.marker_x,
            marker_y=image.marker_y,
            marker_px=image.marker_px,
            marker_py=image.marker_py
        )

        db.session.add(new_image)

    db.session.commit()

    return new_revision


# =========================
# WORKFLOW AKTIONEN
# =========================

def start_review(error, user_id=None):

    if not can_start_review(error):
        raise PermissionError(
            "Nur aktuelle Entwürfe können zur Prüfung eingereicht werden."
        )

    error.workflow_status = STATUS_REVIEW

    db.session.commit()

    return error


def return_to_draft(error, user_id=None):

    if not can_return_to_draft(error):
        raise PermissionError(
            "Nur Fehlermeldungen in Prüfung können zur Bearbeitung zurückgegeben werden."
        )

    error.workflow_status = STATUS_DRAFT
    error.released_at = None
    error.released_by_id = None

    db.session.commit()

    return error


def release(error, user_id):

    if not can_release(error):
        raise PermissionError(
            "Nur Fehlermeldungen in Prüfung können freigegeben werden."
        )

    error.workflow_status = STATUS_RELEASED
    error.released_at = datetime.utcnow()
    error.released_by_id = user_id

    db.session.commit()

    return error


def close(error, user_id=None):

    if not can_close(error):
        raise PermissionError(
            "Nur freigegebene Fehlermeldungen können geschlossen werden."
        )

    error.workflow_status = STATUS_CLOSED

    db.session.commit()

    return error


# Kompatibilität, falls irgendwo noch reopen importiert wird
def reopen(error):

    return return_to_draft(error)
    
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
