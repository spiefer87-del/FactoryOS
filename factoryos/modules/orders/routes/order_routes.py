
@orders_bp.route("/<int:order_id>")
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("orders/detail.html", order=order)
