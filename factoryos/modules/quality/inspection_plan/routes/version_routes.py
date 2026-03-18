from datetime import datetime

from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from factoryos.extensions import db

from factoryos.modules.quality.inspection_plan.services.section_service import add_section
from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change
from factoryos.modules.quality.inspection_plan.services.revision_service import create_new_revision
from factoryos.modules.quality.gauges.models import Gauge

from ..models import (
    QualityInspectionSection,
    QualityInspectionCharacteristic,
    Gauge
)

from . import bp


@bp.route("/<int:plan_id>/version/<int:version_id>/edit", methods=["GET","POST"])
@login_required
def quality_version_edit(plan_id, version_id):

    version = (
        QualityInspectionPlanVersion.query
        .options(
            selectinload(QualityInspectionPlanVersion.sections)
            .selectinload(QualityInspectionSection.characteristics),

            selectinload(QualityInspectionPlanVersion.sections)
            .selectinload(QualityInspectionSection.images),

            selectinload(QualityInspectionPlanVersion.sections)
            .selectinload(QualityInspectionSection.snippets),

            selectinload(QualityInspectionPlanVersion.sections)
            .selectinload(QualityInspectionSection.gauge_checks),
        )
        .get_or_404(version_id)
    )

    gauges = (
        Gauge.query
        .filter_by(status="active")
        .order_by(Gauge.gauge_no)
        .all()
    )

    if request.method == "POST":

        add_type = request.form.get("add_section_type")

        if add_type and version.status == "draft":
            add_section(version, add_type)
            return redirect(request.url)

        if request.form.get("release_version"):

            if not version.is_dirty:
                return redirect(request.url)

            version.status = "released"
            version.released_at = datetime.utcnow()
            version.released_by_id = current_user.id
            version.is_dirty = False

            log_change(
                version,
                "RELEASE",
                f"Version {version.revision} freigegeben"
            )

            db.session.commit()

        return redirect(request.url)

    return render_template(
        "qm_builder.html",
        version=version,
        versions=version.plan.versions,
        gauges=gauges
    )


@bp.route("/<int:version_id>/new_revision", methods=["POST"])
@login_required
def quality_new_revision(version_id):

    new_version = create_new_revision(
        version_id,
        current_user.id
    )

    return redirect(
        url_for(
            "inspection.quality_version_edit",
            plan_id=new_version.plan_id,
            version_id=new_version.id
        )
    )
