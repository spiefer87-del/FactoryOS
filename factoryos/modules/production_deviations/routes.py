from flask import Blueprint,render_template,request,abort,redirect,url_for,flash
from flask_login import login_required,current_user
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.orders.models import Order
from factoryos.modules.production.services.order_statistics import order_statistics,local_label,duration
from factoryos.modules.production.services.machine_control_service import acquire_control_lock,TERMINAL
from .models import ProductionDeviationConfirmation as Confirmation
from .service import REASONS

bp=Blueprint('production_deviations',__name__,url_prefix='/production/deviations')

QUANTITY_ACTION='correct_quantity'

def quantity_edit_url(order):
    if (has_permission(current_user,'orders.edit') and not order.is_project and not order.sampling
            and not order.completion and (order.status or '').lower() not in TERMINAL):
        return url_for('orders.edit',order_id=order.id,focus='quantity',_anchor='order-quantity-section')
    return None

@bp.route('/order/<int:order_id>',methods=['GET','POST'])
@login_required
@permission_required('production.confirm_deviation')
def confirm(order_id):
    order=Order.query.get_or_404(order_id)
    if not has_permission(current_user,'sampling.view' if order.sampling else 'orders.view'):abort(403)
    error=None;status=200;values={'category':'','reason':''}
    if request.method=='POST':
        if not valid_csrf():abort(400)
        if request.form.get('category')==QUANTITY_ACTION:
            target=quantity_edit_url(order)
            if not target:abort(403)
            # Navigation only: this action neither confirms a deviation nor books quantities.
            return redirect(target,code=303)
        acquire_control_lock()
        order=db.session.get(Order,order_id)
        if not has_permission(current_user,'production.confirm_deviation') or not has_permission(current_user,'sampling.view' if order.sampling else 'orders.view'):
            db.session.rollback();abort(403)
    stats=order_statistics(order);deviation=stats['deviation']
    if request.method=='POST':
        values={k:request.form.get(k,'').strip() for k in values}
        if not deviation['kind'] or request.form.get('signature')!=deviation['signature']:error='Datengrundlage geändert. Bitte die aktuelle Abweichung erneut prüfen.';status=409
        elif values['category'] not in REASONS or not 10<=len(values['reason'])<=2000:error='Bitte einen Grund auswählen und eine Erläuterung mit 10 bis 2000 Zeichen eingeben.';status=422
        elif request.form.get('confirmed')!='yes':error='Bitte Prüfung der Abweichung ausdrücklich bestätigen.';status=422
        else:
            entry=Confirmation(order_id=order.id,user_id=current_user.id,signature=deviation['signature'],kind=deviation['kind'],category=values['category'],reason=values['reason'],snapshot=deviation['snapshot'])
            db.session.add(entry)
            log_change('order',order.id,'update',entity_name=order.order_no,category='production_deviation',changes={'deviation_confirmation':{'reason':values['reason'],'category':values['category'],'snapshot':deviation['snapshot']}})
            db.session.commit();flash('Abweichung mit Begründung bestätigt. Sollwerte, Mengen und Auftragsstatus bleiben unverändert.','success')
            return redirect(url_for('orders.detail',order_id=order.id),code=303)
        db.session.rollback()
    return render_template('production/deviation_confirm.html',order=order,statistics=stats,deviation=deviation,reasons=REASONS,values=values,error=error,local_label=local_label,duration=duration,quantity_action=QUANTITY_ACTION,quantity_edit_url=quantity_edit_url(order)),status
