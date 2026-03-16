from flask import render_template
from flask_login import login_required
from factoryos.modules.orders.models import Order
from . import bp

@bp.route("/<int:order_id>")
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("orders/detail.html", order=order)
