from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from factoryos.extensions import db
from factoryos.core.services.change_log_service import log_change
from ..models import Customer

bp = Blueprint("customers", __name__, url_prefix="/masterdata/customers")
FIELDS = {"customer_no": 50, "name": 200, "contact": 150, "email": 200,
          "phone": 80, "street": 200, "postal_code": 30, "city": 120,
          "country": 100, "notes": 10000}


@bp.route("/")
@login_required
def overview():
    customers = Customer.query.order_by(Customer.customer_no).all()
    return render_template("masterdata/customers/list.html", customers=customers)


@bp.route("/<int:customer_id>")
@login_required
def detail(customer_id):
    return render_template("masterdata/customers/detail.html",
                           customer=Customer.query.get_or_404(customer_id))


def save_form(customer=None):
    values = {key: request.form.get(key, "").strip() for key in FIELDS}
    values["active"] = request.form.get("active") == "yes"
    errors = []
    if not values["customer_no"] or not values["name"]:
        errors.append("Kundennummer und Name sind erforderlich.")
    if any(len(values[key]) > limit for key, limit in FIELDS.items()):
        errors.append("Ein Feld überschreitet die zulässige Länge.")
    duplicate = Customer.query.filter_by(customer_no=values["customer_no"]).first()
    if duplicate and (customer is None or duplicate.id != customer.id):
        errors.append("Diese Kundennummer ist bereits vergeben.")
    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template("masterdata/customers/form.html", customer=customer, values=values), 400
    creating = customer is None
    customer = customer or Customer()
    changes = {key: {"old": getattr(customer, key), "new": value}
               for key, value in values.items() if getattr(customer, key) != value}
    for key, value in values.items():
        setattr(customer, key, value)
    db.session.add(customer)
    try:
        db.session.flush()
        log_change("customer", customer.id, "create" if creating else "update",
                   changes=changes, category="masterdata", entity_name=customer.customer_no)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Kundennummer bereits vorhanden. Bitte prüfen.", "danger")
        return render_template("masterdata/customers/form.html", customer=customer, values=values), 400
    flash("Kunde gespeichert.", "success")
    return redirect(url_for("customers.detail", customer_id=customer.id))


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        return save_form()
    return render_template("masterdata/customers/form.html", customer=None, values={"active": True})


@bp.route("/<int:customer_id>/edit", methods=["GET", "POST"])
@login_required
def edit(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    if request.method == "POST":
        return save_form(customer)
    return render_template("masterdata/customers/form.html", customer=customer,
                           values={key: getattr(customer, key) for key in (*FIELDS, "active")})


@bp.route("/<int:customer_id>/delete", methods=["POST"])
@login_required
def delete(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    from factoryos.modules.sampling.models import SamplingOrder
    if SamplingOrder.query.filter_by(customer_id=customer.id).first():
        flash("Dieser Kunde wird von einem Musterungsauftrag verwendet. Bitte bei Bedarf deaktivieren.", "warning")
        return redirect(url_for("customers.detail", customer_id=customer.id))
    if customer.articles:
        flash("Der Kunde ist Artikeln zugeordnet. Bitte zuerst die Zuordnung entfernen oder den Kunden deaktivieren.", "warning")
        return redirect(url_for("customers.detail", customer_id=customer.id))
    log_change("customer", customer.id, "delete", category="masterdata",
               entity_name=customer.customer_no)
    db.session.delete(customer)
    db.session.commit()
    flash("Kunde gelöscht.", "success")
    return redirect(url_for("customers.overview"))

