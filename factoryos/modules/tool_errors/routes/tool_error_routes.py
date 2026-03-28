from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user

from . import bp

from ..queries.tool_error_queries import (
    get_tool_errors,
    get_tool_error
)

from ..services.tool_error_service import (
    create_tool_error,
    delete_tool_error
)


@bp.route("/list")
@login_required
def list():

    errors = get_tool_errors()

    return render_template(
        "/tool_errors/list.html",
        errors=errors
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def tool_error_create():

    if request.method == "POST":

        create_tool_error(request.form, current_user.id)

        return redirect(url_for("production.tool_errors"))

    return render_template(
        "tool_errors/create.html"
    )


@bp.route("/<int:error_id>")
@login_required
def tool_error_detail(error_id):

    error = get_tool_error(error_id)

    return render_template(
        "tool_errors/detail.html",
        error=error
    )


@bp.route("/delete/<int:error_id>")
@login_required
def tool_error_delete(error_id):

    error = get_tool_error(error_id)

    delete_tool_error(error)

    return redirect(url_for("tool_error.list"))
