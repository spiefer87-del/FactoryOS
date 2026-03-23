from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_

from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.orders.models import Order
from factoryos.core.auth import role_required

from . import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "schichtleiter")
def projects_create():
    users = User.query.order_by(User.username.asc()).all()
    tools = Tool.query.order_by(Tool.tool_no.asc()).all()

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
            return redirect(url_for("projects.projects_create"))

        # order_no optional -> generieren
        if not order_no:
            order_no = f"PROJ-{tool_no}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        if Order.query.filter_by(order_no=order_no).first():
            flash("Projekt existiert bereits.", "danger")
            return redirect(url_for("projects.projects_create"))

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
        return redirect(url_for("projects.projects_home"))

    return render_template(
        "projects_create.html",
        users=users,
        tools=tools
    )

bp.route("/close/<int:order_id>", methods=["POST"])
@login_required
def projects_close(order_id):
    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dies ist kein Projekt.", "danger")
        return redirect(url_for("projects.projects_home"))

    # Nur Admin/Schichtleiter (oder Admin)
    if current_user.role not in ["admin", "schichtleiter"]:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("projects.projects_home"))

    # Laufende Projekt-Buchungen zu diesem Projekt beenden
    running = (
        TimeBooking.query
        .filter_by(order_id=order.id, process="PROJEKT")
        .filter(TimeBooking.end_time.is_(None))
    )

    for b in running.all():
        b.end_time = datetime.utcnow()

    order.status = "fertig"
    db.session.commit()

    flash("Projekt geschlossen.", "success")
    return redirect(url_for("projects.projects_home"))
