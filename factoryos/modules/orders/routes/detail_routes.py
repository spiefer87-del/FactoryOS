from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from factoryos.core.auth import has_permission
from factoryos.core.queries.change_log_queries import get_logs
from factoryos.modules.production.services.order_statistics import order_statistics, local_label, duration
from factoryos.modules.orders.models import Order
from . import bp

@bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.sampling:
        return redirect(url_for("sampling.detail", sampling_id=order.sampling.id))
    return render_template("orders/detail.html", order=order, statistics=order_statistics(order),
        local_label=local_label,duration=duration,
        can_correct_time=has_permission(current_user,"production.edit_booking_time"),
        can_edit_order=has_permission(current_user,"orders.edit"),
        can_delete_order=has_permission(current_user,"orders.delete"),
        logs=get_logs(entity_type="order",entity_id=order.id,limit=25))
