from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required

from . import bp

from ..services.tool_import_service import (
    import_tools_from_excel
)


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_tools():

    if request.method == "POST":

        file = request.files.get("file")

        if not file:

            flash(
                "Keine Datei ausgewählt",
                "danger"
            )

            return redirect(
                url_for("tools.import_tools")
            )

        created, updated = (
            import_tools_from_excel(file)
        )

        flash(
            f"{created} Werkzeuge importiert, "
            f"{updated} aktualisiert",
            "success"
        )

        return redirect(
            url_for("tools.dashboard")
        )

    return render_template(
        "masterdata/tools/import.html"
    )
