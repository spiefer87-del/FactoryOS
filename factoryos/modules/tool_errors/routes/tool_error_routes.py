#factoryos/modules/tool_errors/routes/tool_error_routes.py
import os

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    flash
)

from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.core.auth import role_required

from . import bp

from ..models import ToolError, ToolErrorImage

from ..queries.tool_error_queries import (
    get_tool_errors,
    get_tool_error
)

from ..services.tool_error_service import (
    create_tool_error,
    update_tool_error,
    delete_tool_error,
    upload_image,
    assign_images_to_error,
    set_tool_status,
    generate_tool_error_pdf
)

from ..services.workflow_service import (
    start_review,
    release,
    close,
    create_revision,
    get_current_revision,
    get_revisions,
    return_to_draft,
    can_edit,
    can_start_review,
    can_release,
    can_close,
    can_create_revision,
    can_return_to_draft,
    ensure_editable
)

from ..constants import (
    WORKFLOW_STATUSES,
    WORKFLOW_STATUS_COLORS
)

from factoryos.modules.masterdata.tools.queries.tool_queries import get_all_tools
from factoryos.modules.tool_errors.models import ToolErrorTitlePreset
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


# =========================
# ROLLEN
# =========================
# Hier eure echten Rollennamen eintragen.

TOOL_ERROR_EDIT_ROLES = (
    "produktion",
    "qm",
    "admin"
)

TOOL_ERROR_REVIEW_ROLES = (
    "qm",
    "admin"
)

TOOL_ERROR_ADMIN_ROLES = (
    "admin",
)


# =========================
# DASHBOARD
# =========================

@bp.route("/")
@login_required
def dashboard():

    errors = get_tool_errors()

    return render_template(
        "tool_errors/dashboard.html",
        errors=errors,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )


# =========================
# LISTE
# =========================

@bp.route("/list")
@login_required
def list_errors():

    errors = get_tool_errors()

    return render_template(
        "tool_errors/list.html",
        errors=errors,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )


# =========================
# CREATE
# =========================

@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def create():

    tools = get_all_tools()

    presets = (
        ToolErrorTitlePreset.query
        .order_by(ToolErrorTitlePreset.title)
        .all()
    )

    if request.method == "POST":

        try:

            error = create_tool_error(
                request.form,
                current_user.id
            )

            assign_images_to_error(
                temp_id=request.form.get("temp_id"),
                error_id=error.id
            )

            flash(
                "Fehlermeldung wurde erstellt.",
                "success"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id,
                    new=1
                )
            )

        except Exception as e:

            flash(
                f"Fehlermeldung konnte nicht erstellt werden: {e}",
                "danger"
            )

            return redirect(request.url)

    return render_template(
        "tool_errors/create.html",
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES,
        error=None
    )


# =========================
# DETAIL
# =========================

@bp.route("/<int:error_id>")
@login_required
def detail(error_id):

    error = get_tool_error(error_id)

    revisions = get_revisions(error)

    return render_template(
        "tool_errors/detail.html",
        error=error,
        revisions=revisions,

        TOOL_STATUSES=TOOL_STATUSES,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS,

        can_edit_error=can_edit(error),
        can_submit_review=can_start_review(error),
        can_return_to_draft=can_return_to_draft(error),
        can_release_error=can_release(error),
        can_close_error=can_close(error),
        can_create_revision=can_create_revision(error)
    )


# =========================
# EDIT
# =========================

@bp.route("/<int:error_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def edit(error_id):

    error = get_tool_error(error_id)

    if not can_edit(error):

        flash(
            "Diese Fehlermeldung ist gesperrt. Bitte zur Bearbeitung zurückgeben oder eine neue Revision erstellen.",
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=error.id
            )
        )

    tools = get_all_tools()

    presets = (
        ToolErrorTitlePreset.query
        .order_by(ToolErrorTitlePreset.title)
        .all()
    )

    if request.method == "POST":

        try:

            update_tool_error(
                error,
                request.form
            )

            assign_images_to_error(
                temp_id=request.form.get("temp_id"),
                error_id=error.id
            )

            flash(
                "Fehlermeldung wurde aktualisiert.",
                "success"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        except PermissionError as e:

            flash(
                str(e),
                "danger"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        except Exception as e:

            flash(
                f"Fehlermeldung konnte nicht gespeichert werden: {e}",
                "danger"
            )

            return redirect(request.url)

    return render_template(
        "tool_errors/edit.html",
        error=error,
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES
    )


# =========================
# TEMP / IMAGE UPLOAD
# =========================

@bp.route("/upload_temp_image", methods=["POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def upload_temp():

    try:

        image = upload_image(
            file=request.files.get("image"),
            marker_x=request.form.get("marker_x"),
            marker_y=request.form.get("marker_y"),
            marker_px=request.form.get("marker_px"),
            marker_py=request.form.get("marker_py"),
            description=request.form.get("description"),
            temp_id=request.form.get("temp_id"),
            tool_error_id=request.form.get("tool_error_id")
        )

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": f"Upload fehlgeschlagen: {e}"
        }), 500

    if not image:

        return jsonify({
            "success": False,
            "error": "Upload fehlgeschlagen"
        }), 400

    html = render_template(
        "components/image_card.html",
        image=image,
        editable=True,
        marker_number=1
    )

    return jsonify({
        "success": True,
        "image_id": image.id,
        "html": html
    })


# =========================
# IMAGE DELETE
# =========================

@bp.route("/delete_temp_image/<int:image_id>", methods=["POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def delete_temp_image(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    try:

        if image.tool_error_id:

            error = ToolError.query.get(image.tool_error_id)

            if error:
                ensure_editable(error)

        image_path = os.path.join(
            "uploads",
            "tool_errors",
            os.path.basename(image.image_path)
        )

        full_path = os.path.join(
            os.getcwd(),
            "factoryos",
            "static",
            image_path
        )

        same_file_used = (
            ToolErrorImage.query
            .filter(
                ToolErrorImage.image_path == image.image_path,
                ToolErrorImage.id != image.id
            )
            .count()
        )

        if same_file_used == 0 and os.path.exists(full_path):
            os.remove(full_path)

        db.session.delete(image)
        db.session.commit()

        return jsonify({
            "success": True
        })

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# IMAGE GET
# =========================

@bp.route("/image/<int:image_id>")
@login_required
def get_image(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    return jsonify({
        "id": image.id,
        "image_url": url_for(
            "static",
            filename=image.image_path
        ),
        "marker_x": image.marker_x,
        "marker_y": image.marker_y,
        "marker_px": image.marker_px,
        "marker_py": image.marker_py,
        "description": image.description
    })


# =========================
# MARKER UPDATE
# =========================

@bp.route("/image/<int:image_id>/marker", methods=["POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def update_marker(image_id):

    image = ToolErrorImage.query.get_or_404(image_id)

    try:

        if image.tool_error_id:

            error = ToolError.query.get(image.tool_error_id)

            if error:
                ensure_editable(error)

        data = request.get_json() or {}

        image.marker_x = float(data["marker_x"])
        image.marker_y = float(data["marker_y"])

        image.marker_px = int(data["marker_px"])
        image.marker_py = int(data["marker_py"])

        image.description = data.get(
            "description",
            image.description
        )

        db.session.commit()

        return jsonify({
            "success": True
        })

    except PermissionError as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 403

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================
# START REVIEW
# =========================

@bp.route("/<int:error_id>/start-review")
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def start_review_route(error_id):

    error = get_tool_error(error_id)

    try:

        start_review(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde zur Prüfung eingereicht.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# RETURN TO DRAFT
# =========================

@bp.route("/<int:error_id>/return-to-draft")
@login_required
@role_required(*TOOL_ERROR_REVIEW_ROLES)
def return_to_draft_route(error_id):

    error = get_tool_error(error_id)

    try:

        return_to_draft(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde zur Bearbeitung zurückgegeben. Nach Änderungen muss sie erneut zur Prüfung eingereicht werden.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# RELEASE
# =========================

@bp.route("/<int:error_id>/release")
@login_required
@role_required(*TOOL_ERROR_REVIEW_ROLES)
def release_route(error_id):

    error = get_tool_error(error_id)

    try:

        release(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde freigegeben.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# CLOSE
# =========================

@bp.route("/<int:error_id>/close")
@login_required
@role_required(*TOOL_ERROR_REVIEW_ROLES)
def close_route(error_id):

    error = get_tool_error(error_id)

    try:

        close(
            error,
            current_user.id
        )

        flash(
            "Fehlermeldung wurde geschlossen.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# NEW REVISION
# =========================

@bp.route("/<int:error_id>/new-revision")
@login_required
@role_required(*TOOL_ERROR_REVIEW_ROLES)
def new_revision(error_id):

    error = get_tool_error(error_id)

    current = get_current_revision(error)

    if not can_create_revision(current):

        flash(
            "Eine neue Revision kann nur aus einer freigegebenen oder geschlossenen Version erstellt werden.",
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=current.id
            )
        )

    try:

        revision = create_revision(
            current,
            current_user.id
        )

        flash(
            f"Neue Revision {revision.revision} wurde erstellt.",
            "success"
        )

        return redirect(
            url_for(
                "tool_error.edit",
                error_id=revision.id
            )
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=current.id
            )
        )


# =========================
# TOOL STATUS
# =========================

@bp.route("/<int:error_id>/set-tool-status", methods=["POST"])
@login_required
@role_required(*TOOL_ERROR_EDIT_ROLES)
def set_tool_status_route(error_id):

    error = get_tool_error(error_id)

    try:

        ensure_editable(error)

        status = request.form.get("tool_status")

        if not status and request.is_json:
            status = request.json.get("tool_status")

        if not status:
            flash(
                "Kein Werkzeugstatus übergeben.",
                "danger"
            )

            return redirect(
                url_for(
                    "tool_error.detail",
                    error_id=error.id
                )
            )

        set_tool_status(
            error.id,
            status
        )

        flash(
            "Werkzeugstatus wurde aktualisiert.",
            "success"
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# =========================
# DELETE
# =========================

@bp.route("/<int:error_id>/delete", methods=["POST"])
@login_required
@role_required(*TOOL_ERROR_ADMIN_ROLES)
def delete(error_id):

    error = get_tool_error(error_id)

    try:

        delete_tool_error(error)

        flash(
            "Fehlermeldung wurde gelöscht.",
            "success"
        )

        return redirect(
            url_for("tool_error.list_errors")
        )

    except PermissionError as e:

        flash(
            str(e),
            "danger"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=error.id
            )
        )


# =========================
# PDF EXPORT
# =========================

@bp.route("/<int:error_id>/export-pdf")
@login_required
def export_pdf(error_id):

    error = get_tool_error(error_id)

    pdf = generate_tool_error_pdf(error)

    response = make_response(
        pdf.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f"inline; filename={error.error_no}.pdf"
    )

    return response


from flask import (
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    make_response,
    flash
)
from flask_login import login_required, current_user

from . import bp

from ..queries.tool_error_queries import (
    get_tool_errors,
    get_tool_error
)

from ..services.tool_error_service import (
    create_tool_error,
    update_tool_error,
    delete_tool_error,
    upload_image,
    assign_images_to_error,
    set_tool_status,
    generate_tool_error_pdf
)

from ..services.workflow_service import (
    start_review,
    release,
    close,
    create_revision,
    get_current_revision
)

from ..constants import (
    WORKFLOW_STATUSES,
    WORKFLOW_STATUS_COLORS
)

from factoryos.modules.masterdata.tools.queries.tool_queries import get_all_tools
from factoryos.modules.tool_errors.models import (
    ToolErrorTitlePreset
)

from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


@bp.route("/")
@login_required
def dashboard():

    return render_template(
        "tool_errors/dashboard.html"
    )

# =========================
# LIST
# =========================
@bp.route("/list")
@login_required
def list():
    errors = get_tool_errors()

    return render_template(
        "tool_errors/list.html",
        errors=errors
    )


# =========================
# CREATE PAGE
# =========================
@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    tools = get_all_tools()

    presets = ToolErrorTitlePreset.query\
        .filter_by(active=True)\
        .order_by(ToolErrorTitlePreset.sort_order)\
        .all()

    if request.method == "POST":

        error = create_tool_error(request.form, current_user.id)

        # 🔥 TEMP BILDER ZUWEISEN
        assign_images_to_error(
            temp_id=request.form.get("temp_id"),
            error_id=error.id
        )

        return redirect(url_for("tool_error.detail", error_id=error.id,new=1))

    return render_template(
        "tool_errors/create.html",
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )

# =========================
# EDIT
# =========================

@bp.route("/<int:error_id>/edit", methods=["GET", "POST"])
@login_required
def edit(error_id):

    error = get_tool_error(error_id)

    tools = get_all_tools()

    presets = (
        ToolErrorTitlePreset.query
        .filter_by(active=True)
        .order_by(ToolErrorTitlePreset.sort_order)
        .all()
    )

    if request.method == "POST":

        update_tool_error(
            error,
            request.form
        )

        assign_images_to_error(
            temp_id=request.form.get("temp_id"),
            error_id=error.id
        )

        flash(
            "Fehlermeldung wurde aktualisiert.",
            "success"
        )

        return redirect(
            url_for(
                "tool_error.detail",
                error_id=error.id
            )
        )

    return render_template(
        "tool_errors/edit.html",
        error=error,
        tools=tools,
        presets=presets,
        TOOL_STATUSES=TOOL_STATUSES,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )
    
# =========================
# TEMP IMAGE UPLOAD (AJAX)
# =========================
@bp.route("/upload_temp_image", methods=["POST"])
@login_required
def upload_temp():

    image = upload_image(
        file=request.files.get("image"),
        marker_x=request.form.get("marker_x"),
        marker_y=request.form.get("marker_y"),
        marker_px=request.form.get("marker_px"),
        marker_py=request.form.get("marker_py"),
        description=request.form.get("description"),
        temp_id=request.form.get("temp_id"),
        tool_error_id=request.form.get("tool_error_id")
    )

    if not image:
        return jsonify({"error": "Upload fehlgeschlagen"}), 400
    
    html = render_template(
        "components/image_card.html",
        image=image,
        editable=True,
        marker_number=1
    )
    
    return jsonify({
        "success": True,
        "image_id": image.id,
        "html": html
    })

@bp.route("/delete_temp_image/<int:image_id>", methods=["POST"])
@login_required
def delete_temp_image(image_id):

    from ..models import ToolErrorImage
    from factoryos.extensions import db
    import os
    from flask import current_app

    image = ToolErrorImage.query.get_or_404(image_id)

    # 🔥 Datei löschen
    file_path = os.path.join(current_app.static_folder, image.image_path)

    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(image)
    db.session.commit()

    return jsonify({"success": True})


# =========================
# DETAIL
# =========================
@bp.route("/<int:error_id>")
@login_required
def detail(error_id):

    error = get_tool_error(error_id)

    return render_template(
        "tool_errors/detail.html",
        error=error,
        TOOL_STATUSES=TOOL_STATUSES,
        WORKFLOW_STATUSES=WORKFLOW_STATUSES,
        WORKFLOW_STATUS_COLORS=WORKFLOW_STATUS_COLORS
    )

@bp.route("/<int:error_id>/new-revision")
@login_required
def new_revision(error_id):

    error = get_tool_error(error_id)

    current = get_current_revision(error)

    revision = create_revision(
        current,
        current_user.id
    )
    
    flash(
        f"Revision {revision.revision} wurde erstellt.",
        "success"
    )

    return redirect(
        url_for(
            "tool_error.edit",
            error_id=revision.id
        )
    )

# ==========================================
# START REVIEW
# ==========================================

@bp.route("/<int:error_id>/start-review")
@login_required
def start_review_route(error_id):

    error = get_tool_error(error_id)

    start_review(error)

    flash(
        "Fehlermeldung wurde in Prüfung geschickt.",
        "success"
    )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# ==========================================
# RELEASE
# ==========================================

@bp.route("/<int:error_id>/release")
@login_required
def release_route(error_id):

    error = get_tool_error(error_id)

    release(
        error,
        current_user
    )

    flash(
        "Fehlermeldung wurde freigegeben.",
        "success"
    )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )


# ==========================================
# CLOSE
# ==========================================

@bp.route("/<int:error_id>/close")
@login_required
def close_route(error_id):

    error = get_tool_error(error_id)

    close(error)

    flash(
        "Fehlermeldung wurde geschlossen.",
        "success"
    )

    return redirect(
        url_for(
            "tool_error.detail",
            error_id=error.id
        )
    )
    
@bp.route("/set_tool_status/<int:error_id>", methods=["POST"])
@login_required
def set_tool_status_route(error_id):

    status = request.json.get("status")

    success = set_tool_status(error_id, status)

    if not success:
        return jsonify({"success": False}), 404

    return jsonify({"success": True})

# =========================
# DELETE
# =========================
@bp.route("/delete/<int:error_id>")
@login_required
def delete(error_id):

    error = get_tool_error(error_id)

    delete_tool_error(error)

    return redirect(url_for("tool_error.list"))



# =========================
# Export PDF
# =========================


@bp.route("/<int:error_id>/export_pdf")
@login_required
def export_pdf(error_id):

    error = get_tool_error(error_id)

    pdf_buffer = generate_tool_error_pdf(error)

    response = make_response(pdf_buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=tool_error_{error.error_no}.pdf"

    return response

@bp.route("/image/<int:image_id>")
@login_required
def get_image(image_id):

    from ..models import ToolErrorImage

    image = ToolErrorImage.query.get_or_404(image_id)

    return jsonify({

        "id": image.id,

        "image_url": url_for(
            "static",
            filename=image.image_path
        ),

        "marker_x": image.marker_x,
        "marker_y": image.marker_y,

        "marker_px": image.marker_px,
        "marker_py": image.marker_py,

        "description": image.description

    })

@bp.route("/image/<int:image_id>/marker", methods=["POST"])
@login_required
def update_marker(image_id):

    from ..models import ToolErrorImage
    from factoryos.extensions import db

    image = ToolErrorImage.query.get_or_404(image_id)
    data = request.get_json()

    image.marker_x = float(data["marker_x"])
    image.marker_y = float(data["marker_y"])

    image.marker_px = int(data["marker_px"])
    image.marker_py = int(data["marker_py"])

    image.description = request.json.get(
        "description",
        image.description
    )
    
    db.session.commit()

    html = render_template(
        "components/image_card.html",
        image=image,
        editable=True
    )

    return jsonify({
        "success": True,
        "html": html
    })
    
