from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.tools import ToolMasterdata
from factoryos.modules.production.models import Order, TimeBooking

from sqlalchemy import or_

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

    # Nur meine Projekte (Projektleiter = current_user)
    if only_mine:
        base = base.filter(Order.project_leader_id == current_user.id)

    # Suchfilter
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
    project_count = projects_query.count()

    # Eigene laufende Projektzeiten
    active = (
        TimeBooking.query
        .filter_by(user_id=current_user.id)
        .filter(TimeBooking.end_time.is_(None))
        .filter(TimeBooking.process == "PROJEKT")
        .order_by(TimeBooking.start_time.desc())
        .all()
    )

    # Eigene Historie
    history = (
        TimeBooking.query
        .filter_by(user_id=current_user.id)
        .filter(TimeBooking.process == "PROJEKT")
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

@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin", "schichtleiter")
def projects_create():
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

@bp.route("/start/<int:order_id>", methods=["POST"])
@login_required
def projects_start(order_id):
    order = Order.query.get_or_404(order_id)

    if not order.is_project:
        flash("Dieser Auftrag ist kein Projekt.", "danger")
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
        .filter_by(order_id=order.id)
        .filter(TimeBooking.process == "PROJEKT")
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    for b in running:
        b.end_time = datetime.utcnow()

    order.status = "fertig"
    db.session.commit()

    flash("Projekt geschlossen.", "success")
    return redirect(url_for("projects.projects_home"))



@bp.route("/stop/<int:booking_id>", methods=["GET", "POST"])
@login_required
def projects_stop(booking_id):
    b = TimeBooking.query.get_or_404(booking_id)

    if b.user_id != current_user.id:
        flash("Keine Berechtigung.", "danger")
        return redirect(url_for("projects.projects_home"))

    if b.end_time is not None:
        flash("Dieser Eintrag ist bereits beendet.", "warning")
        return redirect(url_for("projects.projects_home"))

    if b.process != "PROJEKT":
        flash("Dies ist keine Projektbuchung.", "warning")
        return redirect(url_for("projects.projects_home"))

    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        b.comment = comment if comment else None
        b.end_time = datetime.utcnow()
        db.session.commit()

        flash("Projektzeit beendet.", "success")
        return redirect(url_for("projects.projects_home"))

    return render_template("projects_stop.html", b=b)
