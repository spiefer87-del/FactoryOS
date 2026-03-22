from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article

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

    articles = Article.query.all()

    if request.method == "POST":
        article_id = request.form.get("article_id")

        if not article_id:
            flash("Bitte Artikel auswählen", "error")
            return redirect(request.url)
        
        article = Article.query.get(article_id)

        if not article:
            abort(400, "Artikel existiert nicht")

        plan = QualityInspectionPlan(
            article_id=article_id,
            tool_id=request.form.get("tool_id") or None
        )

        db.session.add(plan)
        db.session.flush()  # 🔥 wichtig!

        # 👉 ERSTE VERSION ERZEUGEN
        version = QualityInspectionPlanVersion(
            plan_id=plan.id,
            revision="1.0",
        )
        db.session.add(version)
        db.session.commit()

        return redirect(url_for("inspection.quality_version_edit", plan_id=plan.id, version_id=1))

    return render_template(
        "quality/inspection_plan/create_tool_select.html",
        articles=articles
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
