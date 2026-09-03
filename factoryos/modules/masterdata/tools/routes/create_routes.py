from flask import flash, render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.tool_service import create_tool
from ..services.tool_storage_service import DOCUMENT_CATEGORIES
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        image_files = request.files.getlist("images")
        document_files = request.files.getlist("documents")

        try:
            create_tool(
                request.form,
                image_files,
                document_files=document_files,
                document_category=request.form.get(
                    "document_category",
                    "documents"
                )
            )

        except ValueError as error:
            flash(str(error), "danger")
            return redirect(request.url)

        return redirect(
            url_for("tools.list_tools")
        )

    return render_template(
        "masterdata/tools/create.html",
        TOOL_STATUSES=TOOL_STATUSES,
        DOCUMENT_CATEGORIES=DOCUMENT_CATEGORIES
    )
