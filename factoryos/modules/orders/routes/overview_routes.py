from flask import render_template
from flask_login import login_required
from factoryos.modules.orders.models import Order
from ..services.order_form_service import overview_records
from . import bp

@bp.route("/overview")
@login_required
def overview():
    orders=Order.query.filter(~Order.sampling.has()).order_by(Order.id.desc()).all()
    rows=overview_records(orders)
    return render_template("orders/overview.html",orders=orders,rows=rows,
        open_count=sum((o.status or "").lower() in ("open","offen") for o in orders),
        running_count=sum((o.status or "").lower() in ("in_arbeit","running") for o in orders),
        review_count=sum(bool(row["issues"]) for row in rows))
