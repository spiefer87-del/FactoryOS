from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_

from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.tools import ToolMasterdata
from factoryos.modules.production.models import Order, TimeBooking
from factoryos.core.permissions import role_required

bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/projects"
)


@bp.route("/")
@login_required
def projects_home():

    q = request.args.get("q", "").strip()
    only_mine = request.args.get("only_mine", "0") == "1"

    base = (
        Order.query
        .filter_by(is_project=True)
        .filter(~Order.status.in_(["fertig", "gesperrt"]))
    )

    if only_mine:
        base = base.filter(Order.project_leader_id == current_user.id)

    if q:
        like = f"%{q}%"
        base = base.outerjoin(User, Order.project_leader_id == User.id).filter(
            or_(
                Order.order_no.ilike(like),
                Order.tool_no.ilike(like),
                Order.article.ilike(like),
                Order.description.ilike(like),
                User.username.ilike(like)
            )
        )

    projects_query = base.order_by(Order.tool_no.asc(), Order.order_no.asc())

    projects = projects_query.all()
    project_count = len(projects)

    active = (
        TimeBooking.query
        .filter_by(user_id=current_user.id, process="PROJEKT")
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .all()
    )

    history = (
        TimeBooking.query
        .filter_by(user_id=current_user.id, process="PROJEKT")
        .filter(TimeBooking.end_time.isnot(None))
        .order_by(TimeBooking.start_time.desc())
        .limit(50)
        .all()
    )

    return render_template(
        "projects_home.html",
        projects=projects,
        active=active,
        history=history,
        q=q,
        only_mine=only_mine,
        project_count=project_count
    )

@bp.route("/start/<int:order_id>", methods=["POST"])
@login_required
def projects_start(order_id):
    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dieser Auftrag ist kein Projekt.", "danger")
        return redirect(url_for("projects.projects_home"))
    
    existing = (
        TimeBooking.query
        .filter_by(
            user_id=current_user.id,
            order_id=order.id,
            process="PROJEKT"
        )
        .filter(TimeBooking.end_time.is_(None))
        .first()
    )

    if existing:
        flash("Projekt läuft bereits.", "warning")
        return redirect(url_for("projects.projects_home"))

    # Hinweis wenn bereits Projekte laufen
    running = (
        TimeBooking.query
        .filter_by(user_id=current_user.id, process="PROJEKT")
        .filter(TimeBooking.end_time.is_(None))
        .count()
    )

    if running > 0:
        flash("Hinweis: Du hast bereits ein anderes Projekt aktiv laufen.", "warning")

    b = TimeBooking(
        user_id=current_user.id,
        order_id=order.id,
        machine_id=None,
        type="START",
        process="PROJEKT",
        tool_no=order.tool_no,
        start_time=datetime.utcnow()
    )
    db.session.add(b)
    db.session.commit()

    flash("Projekt gestartet.", "success")
    return redirect(url_for("projects.projects_home"))

@bp.route("/close/<int:order_id>", methods=["POST"])
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
