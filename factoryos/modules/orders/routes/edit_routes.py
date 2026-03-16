from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db


@bp.route("/edit/<int:order_id>", methods=["GET", "POST"])
@login_required
def edit(order_id):

    order = Order.query.get_or_404(order_id)

    if request.method == "POST":

        order.article = request.form.get("article")
        order.article_name = request.form.get("article_name")
        order.description = request.form.get("description")
        order.location = request.form.get("location")
        order.target_qty = request.form.get("target_qty")
        order.status = request.form.get("status")

        db.session.commit()

        flash("Auftrag aktualisiert", "success")

        return redirect(url_for("orders.detail", order_id=order.id))

    return render_template("orders/edit.html", order=order)
