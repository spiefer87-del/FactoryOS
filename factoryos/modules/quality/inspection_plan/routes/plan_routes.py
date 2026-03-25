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

    if request.method == "POST":
        article_id = request.form.get("article_id")
        tool_id = request.form.get("tool_id")

        if not article_id:
            flash("Bitte Artikel auswählen", "error")
            return redirect(request.url)

        if not tool_id:
            flash("Bitte Werkzeug auswählen", "error")
            return redirect(request.url)

        article = Article.query.get(article_id)
        tool = Tool.query.get(tool_id)

        if not article or not tool:
            abort(400, "Ungültige Auswahl")

        # ✅ KORREKT: Artikel + Werkzeug prüfen
        existing = QualityInspectionPlan.query.filter_by(
            article_id=article_id,
            tool_id=tool_id
        ).first()

        if existing:
            latest_version = existing.versions[0] if existing.versions else None

            if not latest_version:
                flash("Plan hat keine Version!", "danger")
                return redirect(url_for("inspection.dashboard"))

            return redirect(url_for(
                "inspection.quality_version_edit",
                plan_id=existing.id,
                version_id=latest_version.id
            ))

        # 🆕 Plan erstellen
        plan = QualityInspectionPlan(
            article_id=article_id,
            tool_id=tool_id
        )

        db.session.add(plan)
        db.session.flush()

        version = QualityInspectionPlanVersion(
            plan_id=plan.id,
            revision="1.0",
            status="draft"
        )

        db.session.add(version)
        db.session.commit()

        return redirect(url_for(
            "inspection.quality_version_edit",
            plan_id=plan.id,
            version_id=version.id
        ))

    return render_template(
        "quality/inspection_plan/create.html",
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

@bp.route("/tools-by-article/<int:article_id>")
@login_required
def tools_by_article(article_id):

    article = Article.query.get_or_404(article_id)

    return [
        {
            "id": t.id,
            "text": f"{t.tool_no} ({t.name or ''})"
        }
        for t in article.tools
    ]
