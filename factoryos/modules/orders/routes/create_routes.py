from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db
from sqlalchemy.exc import IntegrityError
from factoryos.modules.masterdata.articles.models import Article
from ..services.cycle_time import parse_cycle_time
from factoryos.core.services.change_log_service import log_change


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":
        try:
            cycle = parse_cycle_time(request.form.get("cycle_time_s"))
        except ValueError as error:
            flash(str(error), "danger")
            return render_template("orders/create.html", articles=Article.query.order_by(Article.article_no).all()), 400

        order = Order(
            order_no=request.form.get("order_no"),
            article=request.form.get("article"),
            article_name=request.form.get("article_name"),
            description=request.form.get("description"),
            location=request.form.get("location"),
            target_qty=request.form.get("target_qty"),
            cycle_time_s=cycle,
        )

        db.session.add(order)
        try:
            db.session.flush()
            log_change("order", order.id, "create", entity_name=order.order_no, category="orders",
                       changes={"cycle_time_s": {"old": None, "new": cycle}})
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Auftragsnummer fehlt oder ist bereits vergeben.", "danger")
            return render_template("orders/create.html", articles=Article.query.order_by(Article.article_no).all()), 400

        flash("Auftrag erfolgreich erstellt", "success")

        return redirect(url_for("orders.dashboard"))

    return render_template("orders/create.html", articles=Article.query.order_by(Article.article_no).all())
