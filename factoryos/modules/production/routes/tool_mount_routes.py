from uuid import uuid4
from flask import request,render_template,redirect,url_for,flash,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.services.machine_control_service import snapshot,ControlDenied,ControlConflict
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state,tool_label
from . import bp


@bp.route('/machine/<int:machine_id>/tool-state',methods=['GET','POST'])
@login_required
@permission_required('production.setup')
def machine_tool_state(machine_id):
    if not has_permission(current_user,'production.view'):abort(403)
    machine=Machine.query.get_or_404(machine_id);embedded=request.args.get('embedded')=='1';error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            confirm_tool_state(machine_id,current_user.id,request.form.get('command_id'),request.form.get('revision'),
                status=request.form.get('status'),tool_no=request.form.get('tool_no',''),reason=request.form.get('reason',''))
            flash('Werkzeugbestand bestätigt. Es wurden keine Rüstzeiten erfunden und keine Produktion gestartet.','success')
            return redirect(url_for('production.machine_control',machine_id=machine_id,embedded='1' if embedded else None,changed='1'),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:db.session.rollback();error='Werkzeugbestand wurde parallel geändert. Bitte neu laden.';status=409
    state=snapshot(machine_id)
    return render_template('production/control/tool_state.html',machine=machine,embedded=embedded,error=error,
        state=state,tool_label=tool_label(state['tool_mount']),command_id=str(uuid4()),
        expected_revision=request.form.get('revision','') if request.method=='POST' else state['revision'],
        tools=Tool.query.order_by(Tool.tool_no).all(),values=request.form),status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}
