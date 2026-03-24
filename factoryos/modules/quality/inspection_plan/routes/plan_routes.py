from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask import abort

from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool

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

    articles = Article.query.order_by(Article.article_no).all()
    tools = Tool.query.order_by(Tool.tool_no).all()   # 🔥 NEU

    if request.method == "POST":
        article_id = request.form.get("article_id")
        tool_id = request.form.get("tool_id") or None   # 🔥 NEU

        if not article_id:
            flash("Bitte Artikel auswählen", "error")
            return redirect(request.url)
        
        article = Article.query.get(article_id)

        if not article:
            abort(400, "Artikel existiert nicht")

        # 🔒 Duplicate Check
        existing = QualityInspectionPlan.query.filter_by(article_id=article_id).first()
        
        if existing:
            if not existing.versions:
                flash("Plan hat keine Version!", "danger")
                return redirect(url_for("inspection.quality_inspection_plan"))

            latest_version = existing.versions[0]

            return redirect(url_for(
                "inspection.quality_version_edit",
                plan_id=existing.id,
                version_id=latest_version.id
            ))

        # 🆕 Plan erstellen
        plan = QualityInspectionPlan(
            article_id=article_id,
            tool_id=tool_id   # 🔥 HIER WICHTIG
        )

        db.session.add(plan)
        db.session.flush()

        # 🆕 Erste Version
        version = QualityInspectionPlanVersion(
            plan_id=plan.id,
            revision="1.0",
        )

        db.session.add(version)
        db.session.commit()

        return redirect(url_for(
            "inspection.quality_version_edit",
            plan_id=plan.id,
            version_id=version.id
        ))

    return render_template(
        "quality/inspection_plan/create.html",  # 🔥 dein neuer Name
        articles=articles,
        tools=tools   # 🔥 WICHTIG
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
