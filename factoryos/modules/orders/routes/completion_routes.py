from uuid import uuid4
from flask import render_template,request,redirect,url_for,flash,abort
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required
from factoryos.core.access_control import valid_csrf
from factoryos.modules.orders.models import Order
from factoryos.modules.production.services.order_completion_service import complete_order,completion_context
from factoryos.modules.production.services.machine_control_service import ControlConflict,ControlDenied
from factoryos.modules.production.services.order_statistics import local_label
from . import bp


def completion_page(order,source,*,machine=None,embedded=False):
    error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            _,replayed=complete_order(order.id,current_user.id,request.form.get('command_id'),request.form.get('revision'),
                good_qty=request.form.get('good_qty'),scrap_qty=request.form.get('scrap_qty'),reason=request.form.get('reason',''),
                confirmed=request.form.get('confirmed')=='yes',short_confirmed=request.form.get('short_confirmed')=='yes',
                source=source,machine_id=machine.id if machine else None)
            flash('Auftrag war bereits abgeschlossen – keine Doppelbuchung.' if replayed else 'Auftrag mit bestätigten Endmengen abgeschlossen. Kein Folgeauftrag wurde automatisch gestartet.','success')
            if machine:return redirect(url_for('production.machine_control',machine_id=machine.id,embedded='1' if embedded else None,changed='1'),303)
            return redirect(url_for('orders.detail',order_id=order.id),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:
            db.session.rollback();error='Auftrag wurde parallel geändert. Bitte neu laden und Abschluss erneut prüfen.';status=409
    context=completion_context(order)
    # Keep the original revision after a failed POST: a concurrent change must
    # not be silently acknowledged merely by resubmitting the error page.
    expected=request.form.get('revision','') if request.method=='POST' else context['revision']
    return render_template('orders/complete.html',order=order,machine=machine,embedded=embedded,source=source,
        context=context,expected_revision=expected,command_id=str(uuid4()),error=error,
        values=request.form if request.method=='POST' else {},local_label=local_label),status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}


@bp.route('/<int:order_id>/complete',methods=['GET','POST'])
@login_required
@permission_required('orders.complete')
def complete(order_id):
    return completion_page(Order.query.get_or_404(order_id),'office')
