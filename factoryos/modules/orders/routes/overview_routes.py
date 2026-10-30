from flask import render_template
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order


@bp.route("/overview")
@login_required
def overview():

    orders = Order.query.filter(~Order.sampling.has()).order_by(Order.id.desc()).all()

    return render_template(
        "orders/overview.html",
        orders=orders
    )
