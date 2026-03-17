from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.models.tools import Tool
from factoryos.core.auth import role_required

from factoryos.modules.production.services.order_service import (
    get_orders_overview,
    create_production_order,
    update_order,
    delete_order,
    get_order_detail_data,
    import_orders_from_excel
)

from . import bp


@bp.route("/")
@login_required
@role_required("admin", "schichtleiter")
def orders_home():

    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status")

    orders, order_count = get_orders_overview(q, status_filter)

    return render_template(
        "orders_home.html",
        orders=orders,
        q=q,
        status_filter=status_filter,
        order_count=order_count
    )


@bp.route("/create")
@login_required
@role_required("admin", "schichtleiter")
def orders_create():
    return render_template("orders_create_choose.html")


@bp.route("/create/prod", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_create_prod():

    tools = Tool.query.order_by(Tool.tool_no.asc()).all()

    if request.method == "POST":

        success, message = create_production_order(request.form)

        flash(message, "success" if success else "danger")

        if success:
            return redirect(url_for("production_orders.orders_home"))

        return redirect(url_for("production_orders.orders_create_prod"))

    return render_template("orders_create_prod.html", tools=tools)


@bp.route("/edit/<int:order_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_edit(order_id):

    from factoryos.modules.production.models import Order

    order = Order.query.get_or_404(order_id)

    if request.method == "POST":

        success, message = update_order(order_id, request.form)

        flash(message, "success" if success else "danger")

        if success:
            return redirect(url_for("production_orders.orders_home"))

        return redirect(url_for("production_orders.orders_edit", order_id=order_id))

    return render_template("orders_edit.html", order=order)


@bp.route("/<order_no>")
@login_required
def order_detail(order_no):

    data = get_order_detail_data(order_no)

    return render_template("order_detail.html", **data)


@bp.route("/delete/<int:order_id>", methods=["POST"])
@login_required
@role_required("admin")
def orders_delete(order_id):

    success, message = delete_order(order_id)

    flash(message, "success" if success else "danger")

    return redirect(url_for("production_orders.orders_home"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_import():

    if request.method == "POST":

        file = request.files.get("file")

        success, message = import_orders_from_excel(file)

        flash(message, "success" if success else "danger")

        return redirect(url_for("production_orders.orders_home"))

    return render_template("orders_import.html")
