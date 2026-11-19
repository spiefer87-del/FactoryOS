from uuid import uuid4
from flask import request,render_template,redirect,url_for,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from ..services.machine_control_service import execute,snapshot,current_booking,ControlConflict,ControlDenied,TERMINAL
from ..services.idle_context_service import WAIT_REASONS
from ..services.order_statistics import local_label
from . import bp
from ..services.control_selection_service import visible_order,tool_proposal,sampling_ready,validate_tool_choice

@bp.route('/machine/<int:machine_id>/control/setup-finish',methods=['GET','POST'])
@login_required
@permission_required('production.view')
@permission_required('production.setup')
def setup_finish(machine_id):
    machine=Machine.query.get_or_404(machine_id);embedded=request.args.get('embedded')=='1'
    waiting=request.args.get('wait')=='1';error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            mode=request.form.get('finish_mode')
            if not waiting and mode not in ('start','wait'):raise ValueError('Produktionsstart oder Warten wählen.')
            if not waiting and mode=='start' and request.form.get('production_confirmed')!='yes':
                raise ValueError('Tatsächlichen Produktionsbeginn und Voraussetzungen ausdrücklich bestätigen.')
            execute(machine_id,current_user.id,'record_wait' if waiting else 'finish_setup',
                request.form.get('command_id'),request.form.get('revision'),
                order_id=request.form.get('order_id') if not waiting else None,
                finish_mode=None if waiting else mode,wait_reason=request.form.get('wait_reason') if waiting or mode=='wait' else None,
                comment=request.form.get('comment',''))
            return redirect(url_for('production.machine_control',machine_id=machine_id,embedded='1' if embedded else None,changed='1'),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:db.session.rollback();error='Keine Änderung gespeichert. Maschinenstand wurde parallel geändert; bitte neu laden.';status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    expected=request.form.get('revision','') if request.method=='POST' else request.args.get('revision',state['revision'])
    blocked=(len(state['active'])!=1 or not active or active.process!=('FREI' if waiting else 'RUEST')
        or expected!=state['revision'] or (waiting and state['tool_mount']['status']!='mounted'))
    if blocked:error='Maschinenstand passt nicht mehr. Bitte zur Maschinenbedienung zurückkehren und neu laden.';status=409
    orders=Order.query.filter_by(is_project=False).order_by(Order.order_no).all()
    orders=[o for o in orders if (o.status or '').lower() not in TERMINAL and not o.completion
            and (not active or not active.order_id or o.id==active.order_id)
            and (not active or not o.tool_no or o.tool_no==active.tool_no)]
    return render_template('production/control/setup_finish.html',machine=machine,active=active,state=state,
        waiting=waiting,error=error,blocked=blocked,embedded=embedded,command_id=str(uuid4()),
        expected_revision=expected,orders=orders,reasons=WAIT_REASONS,values=request.form,
        can_start=has_permission(current_user,'production.start'),local_label=local_label),status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}

@bp.route('/machine/<int:machine_id>/control/teardown-finish',methods=['GET','POST'])
@login_required
@permission_required('production.view')
@permission_required('production.setup')
def teardown_finish(machine_id):
    machine=Machine.query.get_or_404(machine_id);embedded=request.args.get('embedded')=='1'
    error=None;status=200
    preview=request.form.get('action') in ('preview_selection','preview_tool')
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            if not preview:
                mode=request.form.get('finish_mode')
                if mode not in ('setup','free'):raise ValueError('Direktes Rüsten oder frei stehen lassen auswählen.')
                if mode=='setup':validate_tool_choice('setup',request.form)
                execute(machine_id,current_user.id,'finish_setup',request.form.get('command_id'),request.form.get('revision'),
                    finish_mode=mode,order_id=request.form.get('order_id') if mode=='setup' else None,
                    tool_no=request.form.get('tool_no') if mode=='setup' else None,comment=request.form.get('comment',''))
                return redirect(url_for('production.machine_control',machine_id=machine_id,embedded='1' if embedded else None,changed='1'),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:db.session.rollback();error='Keine Änderung gespeichert. Maschinenstand wurde parallel geändert; bitte neu laden.';status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    expected=request.form.get('revision','') if request.method=='POST' else request.args.get('revision',state['revision'])
    blocked=len(state['active'])!=1 or not active or active.process!='ABRUEST' or expected!=state['revision']
    if blocked:error='Abrüstvorgang oder Maschinenstand wurde geändert. Bitte zur Maschinenbedienung zurückkehren und neu laden.';status=409
    from ..services.planning_service import queue
    from ..models import ProductionPlanEntry
    planned=queue(machine_id)
    assignments={e.order_id:e.machine_id for e in ProductionPlanEntry.query.filter_by(state='queued')}
    orders=[o for o in Order.query.filter_by(is_project=False).order_by(Order.order_no) if visible_order(o,machine_id) and assignments.get(o.id,machine_id)==machine_id]
    tools=Tool.query.order_by(Tool.tool_no).all();tool_map={t.tool_no:t for t in tools}
    catalog={str(o.id):dict(proposal=tool_proposal(o,tool_map),sampling=bool(o.sampling),
        ready=sampling_ready(o,machine_id) if o.sampling else True,
        note=('Musterung: vorbereitet für diese Maschine' if sampling_ready(o,machine_id) else 'Musterung noch nicht für diese Maschine vorbereitet. Vor Zuordnung regulär vorbereiten oder ohne Auftrag rüsten.') if o.sampling else 'Fertigungsauftrag',prepare_url=None) for o in orders}
    selected_order=request.form.get('order_id',str(planned[0].order_id) if planned else '')
    proposal=catalog.get(str(selected_order),{}).get('proposal')
    selected_tool=(proposal['number'] if proposal else '') if request.form.get('action')=='preview_selection' else request.form.get('tool_no',proposal['number'] if proposal else '')
    return render_template('production/control/teardown_finish.html',machine=machine,active=active,state=state,
        blocked=blocked,error=error,embedded=embedded,expected_revision=expected,command_id=str(uuid4()),
        orders=orders,tools=tools,selected_order=selected_order,selected_tool=selected_tool,proposal=proposal,
        selected_info=catalog.get(str(selected_order),{}),selection_data=dict(orders=catalog,stock=None,tools=[dict(number=t.tool_no,name=t.name or '') for t in tools]),
        values=request.form),status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}
