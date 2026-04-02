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
    upload_tool_error_image
)

from factoryos.modules.masterdata.tools.queries.tool_queries import get_all_tools
from factoryos.modules.tool_errors.models import ToolErrorTitlePreset


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
# CREATE (STEP 1 + STEP 2)
# =========================
@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    tools = get_all_tools()

    presets = ToolErrorTitlePreset.query\
        .filter_by(active=True)\
        .order_by(ToolErrorTitlePreset.sort_order)\
        .all()

    # 👉 GET ohne error
    error = None

    if request.method == "POST":
        error = create_tool_error(request.form, current_user.id)

        # 🔥 WICHTIG: NICHT auf detail!
        return redirect(url_for("tool_error.create_with_id", error_id=error.id))

    return render_template(
        "tool_errors/create.html",
        tools=tools,
        presets=presets,
        error=error
    )


# =========================
# CREATE MIT ERROR (UPLOAD MODE)
# =========================
@bp.route("/create/<int:error_id>")
@login_required
def create_with_id(error_id):

    tools = get_all_tools()

    presets = ToolErrorTitlePreset.query\
        .filter_by(active=True)\
        .order_by(ToolErrorTitlePreset.sort_order)\
        .all()

    error = get_tool_error(error_id)

    return render_template(
        "tool_errors/create.html",
        tools=tools,
        presets=presets,
        error=error
    )


# =========================
# DETAIL (READ ONLY)
# =========================
@bp.route("/<int:error_id>")
@login_required
def detail(error_id):

    error = get_tool_error(error_id)

    return render_template(
        "tool_errors/detail.html",
        error=error
    )


# =========================
# IMAGE UPLOAD (AJAX)
# =========================
@bp.route("/upload_image/<int:error_id>", methods=["POST"])
@login_required
def upload_image(error_id):

    image = upload_tool_error_image(
        error_id=error_id,
        file=request.files.get("image"),
        marker_x=request.form.get("marker_x"),
        marker_y=request.form.get("marker_y"),
        description=request.form.get("description"),
        user_id=current_user.id
    )

    if not image:
        return jsonify({"error": "Upload fehlgeschlagen"}), 400

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
