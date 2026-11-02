from flask import render_template
from flask_login import login_required, current_user
from factoryos.core.auth import has_permission

from factoryos.modules.orders.models import Order
from . import bp


@bp.route("/dashboard")
@login_required
def dashboard():

    orders = Order.query.order_by(Order.id.desc()).all()

    return render_template(
        "orders/dashboard.html",
        orders=orders,
        can_import_orders=has_permission(current_user, "orders.excel_import")
    )
