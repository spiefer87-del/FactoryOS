from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.modules.masterdata.tools.service import (
    search_tools,
    create_tool,
    update_tool,
    delete_tool
)

from factoryos.models.tools import ToolMasterdata


tools_bp = Blueprint(
    "tools",
    __name__,
    url_prefix="/masterdata/tools"
)


@tools_bp.route("/")
@login_required
def list_tools():

    q = request.args.get("q", "").strip()

    rows = search_tools(q)

    return render_template(
        "masterdata/tools/list.html",
        rows=rows,
        q=q,
        count=len(rows)
    )


@tools_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        create_tool(request.form)

        flash("Werkzeug gespeichert", "success")

        return redirect(url_for("tools.list_tools"))

    return render_template("masterdata/tools/create.html")


@tools_bp.route("/edit/<int:tool_id>", methods=["GET", "POST"])
@login_required
def edit(tool_id):

    row = ToolMasterdata.query.get_or_404(tool_id)

    if request.method == "POST":

        update_tool(row, request.form)

        flash("Werkzeug aktualisiert", "success")

        return redirect(url_for("tools.list_tools"))

    return render_template("masterdata/tools/edit.html", row=row)


@tools_bp.route("/delete/<int:tool_id>", methods=["POST"])
@login_required
def delete(tool_id):

    delete_tool(tool_id)

    flash("Werkzeug gelöscht", "success")

    return redirect(url_for("tools.list_tools"))