from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import func, or_

from factoryos.extensions import db
from factoryos.modules.production.models import Order, QuantityReport
from factoryos.models.tools import ToolMasterdata
from factoryos.models.user import User
from factoryos.core.permissions import role_required


bp = Blueprint(
    "production_orders",
    __name__,
    url_prefix="/production/orders"
)


@bp.route("/")
@login_required
@role_required("admin", "schichtleiter")
def orders_home():

    q = request.args.get("q", "").strip()

    status_filter = request.args.get("status", None)

    if status_filter is None:
        status_filter = "offen"

    if status_filter == "":
        status_filter = ""

    query = (
        db.session.query(
            Order,
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum")
        )
        .outerjoin(QuantityReport, QuantityReport.order_id == Order.id)
        .group_by(Order.id)
    )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Order.order_no.ilike(like),
                Order.article.ilike(like),
                Order.description.ilike(like),
                Order.tool_no.ilike(like),
            )
        )

    if status_filter in ["offen", "in_arbeit", "fertig", "gesperrt"]:
        query = query.filter(Order.status == status_filter)

    query = query.order_by(Order.order_no.asc())

    rows = query.all()

    orders = []

    for order, good_sum in rows:

        target = order.target_qty or 0
        good = good_sum or 0

        rest = target - good

        if rest < 0:
            rest = 0

        orders.append({
            "order": order,
            "good": int(good),
            "rest": int(rest)
        })

    order_count = len(orders)

    return render_template(
        "admin_orders.html",
        orders=orders,
        q=q,
        status_filter=status_filter,
        order_count=order_count
    )
    
@bp.route("/create", methods=["GET"])
@login_required
@role_required("admin", "schichtleiter")
def orders_create():
    return render_template("orders_create_choose.html")

@bp.route("/create/project", methods=["GET", "POST"])
@login_required
@role_required("admin", "schichtleiter")
def orders_create_project():
    users = User.query.order_by(User.username.asc()).all()
    tools = ToolMasterdata.query.order_by(ToolMasterdata.tool_no.asc()).all()

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()

        tool_no = request.form.get("tool_no", "").strip()

        article = request.form.get("article", "").strip()  # Artikelnummer
        article_name = request.form.get("article_name", "").strip()
        location = request.form.get("location", "").strip()

        reason = request.form.get("reason", "").strip()
        description = request.form.get("description", "").strip()
        project_leader_id = request.form.get("project_leader_id", "").strip()

        # Werkzeug Pflicht
        if not tool_no:
            flash("Werkzeug-Nr. ist Pflicht für Projekte.", "danger")
            return redirect(url_for("admin_orders_create_project"))

        # order_no optional -> generieren
        if not order_no:
            order_no = f"PROJ-{tool_no}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        if Order.query.filter_by(order_no=order_no).first():
            flash("Projekt existiert bereits.", "danger")
            return redirect(url_for("orders_create_project"))

        # Projektleiter optional
        leader_id_int = None
        if project_leader_id:
            try:
                leader_id_int = int(project_leader_id)
            except:
                leader_id_int = None

        # Beschreibung kombinieren
        final_description = reason
        if description:
            final_description = f"{reason} - {description}"

        o = Order(
            order_no=order_no,
            article=article if article else None,
            article_name=article_name if article_name else None,
            location=location if location else None,
            tool_no=tool_no,
            description=final_description if final_description else None,
            target_qty=0,
            status="offen",
            is_project=True,
            project_leader_id=leader_id_int
        )
        db.session.add(o)
        db.session.commit()

        flash("Projekt angelegt.", "success")
        return redirect(url_for("projects_dashboard"))

    return render_template(
        "orders_create_project.html",
        users=users,
        tools=tools
    )


@bp.route("/create/prod", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_create_prod():
    tools = ToolMasterdata.query.order_by(ToolMasterdata.tool_no.asc()).all()

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()

        article = request.form.get("article", "").strip()  # Artikelnummer
        article_name = request.form.get("article_name", "").strip()
        location = request.form.get("location", "").strip()

        tool_no = request.form.get("tool_no", "").strip()
        description = request.form.get("description", "").strip()
        target_qty = request.form.get("target_qty", "0").strip()
        status = request.form.get("status", "offen")

        if not order_no:
            flash("Bitte Auftragsnummer angeben.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        if Order.query.filter_by(order_no=order_no).first():
            flash("Auftrag existiert bereits.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        try:
            target_qty_int = int(target_qty)
        except:
            target_qty_int = 0

        if target_qty_int <= 0:
            flash("Sollmenge muss größer 0 sein.", "danger")
            return redirect(url_for("admin_orders_create_prod"))

        o = Order(
            order_no=order_no,
            article=article if article else None,
            article_name=article_name if article_name else None,
            location=location if location else None,
            tool_no=tool_no if tool_no else None,
            description=description if description else None,
            target_qty=target_qty_int,
            status=status,
            is_project=False
        )
        db.session.add(o)
        db.session.commit()

        flash("Fertigungsauftrag angelegt.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("orders_create_prod.html", tools=tools)


@bp.route("/edit/<int:order_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_edit(order_id):
    o = Order.query.get_or_404(order_id)

    if request.method == "POST":
        order_no = request.form.get("order_no", "").strip()
        article = request.form.get("article", "").strip()
        tool_no = request.form.get("tool_no", "").strip()
        description = request.form.get("description", "").strip()
        target_qty = request.form.get("target_qty", "0").strip()
        status = request.form.get("status", "offen")

        if not order_no:
            flash("Bitte Auftragsnummer angeben.", "danger")
            return redirect(url_for("admin_orders_edit", order_id=order_id))

        existing = Order.query.filter(Order.order_no == order_no, Order.id != o.id).first()
        if existing:
            flash("Auftragsnummer existiert bereits.", "danger")
            return redirect(url_for("orders_edit", order_id=order_id))

        try:
            target_qty_int = int(target_qty)
        except:
            target_qty_int = 0

        o.order_no = order_no
        o.article = article if article else None
        o.tool_no = tool_no if tool_no else None
        o.description = description if description else None
        o.target_qty = target_qty_int
        o.status = status

        db.session.commit()
        flash("Auftrag gespeichert.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("orders_edit.html", order=o)

@bp.route("/delete/<int:order_id>", methods=["POST"])
@login_required
@role_required("admin")
def orders_delete(order_id):
    o = Order.query.get_or_404(order_id)

    # Prüfen ob Auftrag aktiv läuft
    running = (
        TimeBooking.query
        .filter_by(order_id=o.id)
        .filter(TimeBooking.end_time.is_(None))
        .first()
    )

    if running:
        flash("Auftrag kann nicht gelöscht werden: Es läuft noch eine aktive Buchung.", "danger")
        return redirect(url_for("admin_orders"))

    # abhängige Daten löschen
    TimeBooking.query.filter_by(order_id=o.id).delete()
    QuantityReport.query.filter_by(order_id=o.id).delete()

    db.session.delete(o)
    db.session.commit()

    flash("Auftrag wurde gelöscht.", "success")
    return redirect(url_for("orders"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
@role_required("admin")
def orders_import():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Bitte Excel-Datei auswählen.", "danger")
            return redirect(url_for("admin_orders_import"))

        wb = load_workbook(file, data_only=True)
        ws = wb.active

        # Header lesen
        header = []
        for cell in ws[1]:
            header.append(str(cell.value).strip() if cell.value else "")

        required = ["order_no", "article", "description", "tool_no", "target_qty", "status"]
        for r in required:
            if r not in header:
                flash(f"Spalte fehlt: {r}", "danger")
                return redirect(url_for("admin_orders_import"))

        idx = {name: header.index(name) for name in required}

        created = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            order_no = str(row[idx["order_no"]]).strip() if row[idx["order_no"]] else ""
            if not order_no:
                continue

            # schon vorhanden?
            existing = Order.query.filter_by(order_no=order_no).first()
            if existing:
                skipped += 1
                continue

            article = str(row[idx["article"]]).strip() if row[idx["article"]] else None
            description = str(row[idx["description"]]).strip() if row[idx["description"]] else None
            tool_no = str(row[idx["tool_no"]]).strip() if row[idx["tool_no"]] else None

            try:
                target_qty = int(row[idx["target_qty"]] or 0)
            except:
                target_qty = 0

            status = str(row[idx["status"]]).strip() if row[idx["status"]] else "offen"
            if status not in ["offen", "in_arbeit", "fertig", "gesperrt"]:
                status = "offen"

            o = Order(
                order_no=order_no,
                article=article,
                description=description,
                tool_no=tool_no,
                target_qty=target_qty,
                status=status
            )
            db.session.add(o)
            created += 1

        db.session.commit()

        flash(f"Import fertig: {created} neu, {skipped} übersprungen.", "success")
        return redirect(url_for("admin_orders"))

    return render_template("orders_import.html")
