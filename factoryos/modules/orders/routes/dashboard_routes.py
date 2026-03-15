from flask import render_template
from flask_login import login_required

from factoryos.modules.orders.models import Order
from . import bp


@bp.route("/dashboard")
@login_required
def dashboard():

    orders = Order.query.order_by(Order.id.desc()).all()

    return render_template(
        "orders/dashboard.html",
        orders=orders
    )