from uuid import uuid4
from flask import request,render_template,redirect,url_for,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from ..services.machine_control_service import execute,snapshot,current_booking,ControlConflict,ControlDenied,TERMINAL
from ..services.idle_context_service import WAIT_REASONS
from ..services.order_statistics import local_label
from . import bp

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
