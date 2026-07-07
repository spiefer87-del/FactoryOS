import os
import uuid
import shutil
from datetime import datetime

from flask import current_app
from sqlalchemy import or_

from factoryos.extensions import db
from factoryos.modules.tool_errors.models import ToolError, ToolErrorImage
from factoryos.core.services.change_log_service import log_change


# =========================
# WORKFLOW STATUS
# =========================

STATUS_DRAFT = "draft"
STATUS_REVIEW = "review"
STATUS_RELEASED = "released"
STATUS_CLOSED = "closed"

STATUS_LABELS = {
    STATUS_DRAFT: "Entwurf",
    STATUS_REVIEW: "In Prüfung",
    STATUS_RELEASED: "Freigegeben",
    STATUS_CLOSED: "Geschlossen",
}


def status_label(status):

    return STATUS_LABELS.get(status, status or "-")

# =========================
# Changelog
# =========================
def tool_error_log_name(error):

    tool_no = "-"

    if error.tool:
        tool_no = error.tool.tool_no

    return f"{error.error_no} Rev. {error.revision} ({tool_no})"

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

def close_previous_released_revisions(error):

    root_id = _revision_root_id(error)

    previous_revisions = (
        ToolError.query
        .filter(
            or_(
                ToolError.id == root_id,
                ToolError.parent_error_id == root_id
            ),
            ToolError.id != error.id,
            ToolError.workflow_status == STATUS_RELEASED
        )
        .all()
    )

    for previous in previous_revisions:
        previous.workflow_status = STATUS_CLOSED

    return previous_revisions


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

    log_change(
        entity_type="tool_error",
        entity_id=new_revision.id,
        entity_name=tool_error_log_name(new_revision),
        action="revision_create",
        changes={
            "revision": {
                "old": current.revision,
                "new": new_revision.revision
            },
            "workflow_status": {
                "old": status_label(current.workflow_status),
                "new": status_label(new_revision.workflow_status)
            }
        },
        category="production"
    )

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

    old_status = error.workflow_status

    error.workflow_status = STATUS_REVIEW

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool_error_log_name(error),
        action="start_review",
        changes={
            "workflow_status": {
                "old": status_label(old_status),
                "new": status_label(error.workflow_status)
            }
        },
        category="production"
    )

    db.session.commit()

    return error


def return_to_draft(error, user_id=None):

    if not can_return_to_draft(error):
        raise PermissionError(
            "Nur Fehlermeldungen in Prüfung können zur Bearbeitung zurückgegeben werden."
        )

    old_status = error.workflow_status

    error.workflow_status = STATUS_DRAFT
    error.released_at = None
    error.released_by_id = None

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool_error_log_name(error),
        action="return_to_draft",
        changes={
            "workflow_status": {
                "old": status_label(old_status),
                "new": status_label(error.workflow_status)
            }
        },
        category="production"
    )

    db.session.commit()

    return error


# =========================
# ALTE FREIGEGEBENE REVISIONEN SCHLIESSEN
# =========================

def close_previous_released_revisions(error):

    root_id = _revision_root_id(error)

    previous_revisions = (
        ToolError.query
        .filter(
            or_(
                ToolError.id == root_id,
                ToolError.parent_error_id == root_id
            ),
            ToolError.id != error.id,
            ToolError.workflow_status == STATUS_RELEASED
        )
        .all()
    )

    for previous in previous_revisions:

        old_status = previous.workflow_status

        previous.workflow_status = STATUS_CLOSED

        log_change(
            entity_type="tool_error",
            entity_id=previous.id,
            entity_name=tool_error_log_name(previous),
            action="auto_close",
            changes={
                "workflow_status": {
                    "old": status_label(old_status),
                    "new": status_label(previous.workflow_status)
                },
                "reason": {
                    "old": "-",
                    "new": f"Neue Revision {error.revision} wurde freigegeben"
                }
            },
            category="production"
        )

    return previous_revisions


# =========================
# FREIGEBEN
# =========================

def release(error, user_id):

    if not can_release(error):
        raise PermissionError(
            "Nur Fehlermeldungen in Prüfung können freigegeben werden."
        )

    old_status = error.workflow_status

    error.workflow_status = STATUS_RELEASED
    error.released_at = datetime.utcnow()
    error.released_by_id = user_id

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool_error_log_name(error),
        action="release",
        changes={
            "workflow_status": {
                "old": status_label(old_status),
                "new": status_label(error.workflow_status)
            }
        },
        category="production"
    )

    close_previous_released_revisions(error)

    db.session.commit()

    return error

def close(error, user_id=None):

    if not can_close(error):
        raise PermissionError(
            "Nur freigegebene Fehlermeldungen können geschlossen werden."
        )

    old_status = error.workflow_status

    error.workflow_status = STATUS_CLOSED

    log_change(
        entity_type="tool_error",
        entity_id=error.id,
        entity_name=tool_error_log_name(error),
        action="close",
        changes={
            "workflow_status": {
                "old": status_label(old_status),
                "new": status_label(error.workflow_status)
            }
        },
        category="production"
    )

    db.session.commit()

    return error


# Kompatibilität, falls irgendwo noch reopen importiert wird
def reopen(error):

    return return_to_draft(error)
    

