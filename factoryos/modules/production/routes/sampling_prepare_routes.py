from flask import request,render_template,redirect,url_for,flash,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.sampling.definitions import STATES
from factoryos.modules.production.services.control_selection_service import prepare_sampling as prepare,visible_order
from factoryos.modules.production.services.machine_control_service import snapshot,ControlDenied,ControlConflict
from . import bp


@bp.route('/machine/<int:machine_id>/sampling/<int:sampling_id>/prepare',methods=['GET','POST'])
@login_required
@permission_required('sampling.edit')
def prepare_sampling(machine_id,sampling_id):
    if not has_permission(current_user,'production.view'):abort(403)
    machine=Machine.query.get_or_404(machine_id);record=SamplingOrder.query.get_or_404(sampling_id)
    embedded=request.args.get('embedded')=='1';error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            if request.form.get('confirmed')!='yes':raise ValueError('Maschine, Werkzeug und Übernahme in Bearbeitung bitte bewusst bestätigen.')
            prepare(machine_id,sampling_id,current_user.id,request.form.get('version'),request.form.get('revision'),change_confirmed=request.form.get('change_machine_confirmed')=='yes')
            flash('Musterung für diese Maschine vorbereitet. Werkzeug separat bestätigen und den gewünschten Vorgang bewusst starten. Keine Prüffreigabe erteilt.','success')
            return redirect(url_for('production.machine_control',machine_id=machine_id,order_id=record.order_id,embedded='1' if embedded else None,changed='1'),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:db.session.rollback();error='Musterung wurde parallel geändert. Bitte neu laden und erneut prüfen.';status=409
    state=snapshot(machine_id)
    return render_template('production/control/sampling_prepare.html',machine=machine,record=record,states=STATES,
        embedded=embedded,error=error,blocked=not visible_order(record.order,machine_id),
        foreign_machine=record.machine_id not in (None,machine_id),
        version=request.form.get('version') if request.method=='POST' else record.version,
        revision=request.form.get('revision') if request.method=='POST' else state['revision']),status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}
