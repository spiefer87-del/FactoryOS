from flask import redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from ..services.tool_service import delete_tool


@bp.route("/delete/<int:tool_id>")
@login_required
def delete(tool_id):

    tool = Tool.query.get_or_404(tool_id)
    from factoryos.modules.projects.workspace_models import ToolPartEvent,Link
    from sqlalchemy import inspect
    from factoryos.modules.tool_errors.models import ToolError
    if inspect(db.engine).has_table('project_tool_part_events') and (ToolPartEvent.query.filter_by(tool_id=tool.id).first() or Link.query.join(ToolError,Link.error_id==ToolError.id).filter(ToolError.tool_id==tool.id).first()):
        flash('Werkzeug besitzt eine Projekt-/Reparaturhistorie. Bitte erhalten und Status ändern statt löschen.', 'warning')
        return redirect(url_for('tools.detail',tool_id=tool.id))

    from factoryos.modules.setup_reports.models import SetupReport
    from sqlalchemy import inspect
    if inspect(db.engine).has_table('setup_reports') and SetupReport.query.filter_by(tool_id=tool.id).first():
        flash("Werkzeug besitzt Einstellberichte. Bitte nicht löschen, sondern den Werkzeugstatus ändern.", "warning")
        return redirect(url_for("tools.detail", tool_id=tool.id))

    from factoryos.modules.sampling.models import SamplingOrder
    if SamplingOrder.query.filter_by(tool_id=tool.id).first():
        flash("Dieser Stammdatensatz wird von einem Musterungsauftrag verwendet und kann nicht gelöscht werden.", "warning")
        return redirect(url_for("tools.detail", tool_id=tool.id))
    try:delete_tool(tool)
    except ValueError as error:
        db.session.rollback();flash(str(error),'warning')
        return redirect(url_for('tools.detail',tool_id=tool.id))

    return redirect(url_for("tools.list_tools"))
