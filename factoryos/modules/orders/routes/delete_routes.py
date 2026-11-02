from flask import redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db


@bp.route("/delete/<int:order_id>")
@login_required
def delete(order_id):

    order = Order.query.get_or_404(order_id)
    if order.sampling:
        return redirect(url_for("sampling.detail", sampling_id=order.sampling.id))
    from factoryos.modules.production.models import TimeBooking,QuantityReport,MachineControlState
    from factoryos.modules.production.services.machine_control_service import acquire_control_lock
    acquire_control_lock()
    if (TimeBooking.query.filter_by(order_id=order.id).first() or QuantityReport.query.filter_by(order_id=order.id).first() or
        MachineControlState.query.filter_by(resume_order_id=order.id).first()):
        db.session.rollback()
        flash("Auftrag besitzt Buchungen oder ist an einer Maschine reserviert. Er bleibt zur Nachverfolgung erhalten.","warning")
        return redirect(url_for("orders.detail",order_id=order.id))

    db.session.delete(order)
    db.session.commit()

    flash("Auftrag gelöscht", "warning")

    return redirect(url_for("orders.dashboard"))
