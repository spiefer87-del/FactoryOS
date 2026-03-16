from flask import redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db


@bp.route("/delete/<int:order_id>")
@login_required
def delete(order_id):

    order = Order.query.get_or_404(order_id)

    db.session.delete(order)
    db.session.commit()

    flash("Auftrag gelöscht", "warning")

    return redirect(url_for("orders.dashboard"))
