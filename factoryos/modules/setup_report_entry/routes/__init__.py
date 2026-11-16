from flask import Blueprint, render_template, request, abort, flash, redirect, url_for
from flask_login import login_required,current_user
from sqlalchemy import func
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.modules.masterdata.tools.models import Tool

bp=Blueprint('setup_report_entry',__name__,url_prefix='/masterdata/setup-reports')


@bp.after_request
def private(response):
    response.headers['Cache-Control']='private, no-store'
    return response


@bp.route('/start',methods=['GET','POST'])
@login_required
@permission_required('setup_reports.create')
def start():
    if not has_permission(current_user,'tools.view'):abort(403)
    if request.method=='POST':
        if not valid_csrf():abort(400)
        raw=request.form.get('tool_no','').strip()
        matches=Tool.query.filter(func.lower(Tool.tool_no)==raw.lower()).limit(2).all() if raw and len(raw)<=100 else []
        if len(matches)!=1:
            flash('Bitte eine eindeutige vorhandene Werkzeugnummer auswählen. Es wurde kein Bericht angelegt.','warning')
            return redirect(url_for('setup_report_entry.start'))
        # Reuse the existing guarded creation path; no second report logic.
        from factoryos.modules.setup_reports.routes import create
        return create(matches[0].id)
    return render_template('setup_reports/start.html',tools=Tool.query.order_by(Tool.tool_no).all())
