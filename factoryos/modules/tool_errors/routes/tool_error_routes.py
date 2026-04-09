from flask import render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from . import bp


from ..queries.tool_error_queries import (
    get_tool_errors,
    get_tool_error
)

from ..services.tool_error_service import (
    create_tool_error,
    delete_tool_error,
    upload_temp_image,
    assign_images_to_error,
    set_tool_status
)


from factoryos.modules.masterdata.tools.queries.tool_queries import get_all_tools
from factoryos.modules.tool_errors.models import ToolErrorTitlePreset
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


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
        TOOL_STATUSES=TOOL_STATUSES
    )


# =========================
# TEMP IMAGE UPLOAD (AJAX)
# =========================
@bp.route("/upload_temp_image", methods=["POST"])
@login_required
def upload_temp():

    image = upload_temp_image(
        file=request.files.get("image"),
        marker_x=request.form.get("marker_x"),
        marker_y=request.form.get("marker_y"),
        description=request.form.get("description"),
        temp_id=request.form.get("temp_id")
    )

    if not image:
        return jsonify({"error": "Upload fehlgeschlagen"}), 400

    return jsonify({
        "success": True,
        "image_id": image.id
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
        error=error
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

from flask import make_response
from ..services.tool_error_service import generate_tool_error_pdf


@bp.route("/<int:error_id>/export_pdf")
@login_required
def export_pdf(error_id):

    error = get_tool_error(error_id)

    pdf_buffer = generate_tool_error_pdf(error)

    response = make_response(pdf_buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename=tool_error_{error.error_no}.pdf"

    return response
