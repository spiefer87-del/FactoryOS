from flask import render_template, redirect, url_for
from flask_login import login_required
from factoryos.modules.orders.models import Order
from . import bp

@bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.sampling:
        return redirect(url_for("sampling.detail", sampling_id=order.sampling.id))
    return render_template("orders/detail.html", order=order)
