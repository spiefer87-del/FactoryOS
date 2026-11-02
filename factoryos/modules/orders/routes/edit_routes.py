from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article
from ..services.cycle_time import parse_cycle_time
from factoryos.core.services.change_log_service import log_change


@bp.route("/edit/<int:order_id>", methods=["GET", "POST"])
@login_required
def edit(order_id):

    order = Order.query.get_or_404(order_id)
    if order.sampling:
        return redirect(url_for("sampling.detail", sampling_id=order.sampling.id))

    if request.method == "POST":
        try:
            cycle = parse_cycle_time(request.form.get("cycle_time_s")) if not order.is_project else order.cycle_time_s
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("orders/edit.html", order=order, articles=Article.query.order_by(Article.article_no).all()), 400

        old_cycle = order.cycle_time_s
        order.article = request.form.get("article")
        order.article_name = request.form.get("article_name")
        order.description = request.form.get("description")
        order.location = request.form.get("location")
        order.target_qty = request.form.get("target_qty")
        order.cycle_time_s = cycle
        order.status = request.form.get("status", order.status)
        if old_cycle != cycle:
            log_change("order", order.id, "update", entity_name=order.order_no, category="orders",
                       changes={"cycle_time_s": {"old": old_cycle, "new": cycle}})

        db.session.commit()

        flash("Auftrag aktualisiert", "success")

        return redirect(url_for("orders.detail", order_id=order.id))

    return render_template("orders/edit.html", order=order, articles=Article.query.order_by(Article.article_no).all())
