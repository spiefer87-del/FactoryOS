from flask import flash, render_template, request, redirect, url_for
from flask_login import login_required

from . import bp
from ..services.tool_service import update_tool
from ..services.tool_storage_service import (
    DOCUMENT_CATEGORIES,
    list_tool_documents,
)
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.shared.constants import TOOL_STATUSES


@bp.route("/edit/<int:tool_id>", methods=["GET", "POST"])
@login_required
def edit(tool_id):

    tool = Tool.query.get_or_404(tool_id)

    if request.method == "POST":

        image_files = request.files.getlist("images")
        document_files = request.files.getlist("documents")
        delete_ids = request.form.getlist("delete_images")

        try:
            update_tool(
                tool,
                request.form,
                image_files,
                delete_ids,
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
        "masterdata/tools/edit.html",
        tool=tool,
        TOOL_STATUSES=TOOL_STATUSES,
        documents=list_tool_documents(tool.tool_no),
        DOCUMENT_CATEGORIES=DOCUMENT_CATEGORIES
    )
