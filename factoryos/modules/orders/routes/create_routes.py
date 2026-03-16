from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from . import bp
from factoryos.modules.orders.models import Order
from factoryos.extensions import db


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():

    if request.method == "POST":

        order = Order(
            order_no=request.form.get("order_no"),
            article=request.form.get("article"),
            article_name=request.form.get("article_name"),
            description=request.form.get("description"),
            location=request.form.get("location"),
            target_qty=request.form.get("target_qty"),
        )

        db.session.add(order)
        db.session.commit()

        flash("Auftrag erfolgreich erstellt", "success")

        return redirect(url_for("orders.dashboard"))

    return render_template("orders/create.html")
