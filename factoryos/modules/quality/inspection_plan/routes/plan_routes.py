from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.models.tools import Tool

from factoryos.core.auth import role_required

from ..models import (
    QualityInspectionPlan,
    QualityInspectionPlanVersion
)

from . import bp


@bp.route("/inspectionplan")
@login_required
def quality_inspection_plan():

    plans = (
        QualityInspectionPlan.query
        .order_by(QualityInspectionPlan.id.desc())
        .all()
    )

    return render_template(
        "quality/inspection_plan/dashboard.html",
        plans=plans
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("qm", "admin")
def quality_create():

    tools = Tool.query.order_by(Tool.tool_no).all()

    if request.method == "POST":

        tool_id = request.form.get("tool_id")

        if not tool_id:
            flash("Bitte Werkzeug auswählen", "warning")
            return redirect(url_for("inspection.quality_create"))

        # Plan erstellen
        plan = QualityInspectionPlan(
            tool_id=tool_id,
            created_by_id=current_user.id
        )

        db.session.add(plan)
        db.session.flush()

        # Version erstellen
        version = QualityInspectionPlanVersion(
            plan_id=plan.id,
            revision="A",
            status="draft"
        )

        db.session.add(version)
        db.session.commit()

        return redirect(
            url_for(
                "inspection.quality_version_edit",
                plan_id=plan.id,
                version_id=version.id
            )
        )

    return render_template(
        "quality/inspection_plan/create_tool_select.html",
        tools=tools
    )


@bp.route("/<int:plan_id>/delete", methods=["POST"])
@login_required
def quality_delete_plan(plan_id):

    plan = QualityInspectionPlan.query.get_or_404(plan_id)

    if any(v.status == "released" for v in plan.versions):
        flash("Freigegebene Prüfpläne können nicht gelöscht werden.", "danger")
        return redirect(url_for("inspection.quality_inspection_plan"))

    db.session.delete(plan)
    db.session.commit()

    flash("Prüfplan wurde gelöscht", "success")

    return redirect(url_for("inspection.quality_inspection_plan"))
