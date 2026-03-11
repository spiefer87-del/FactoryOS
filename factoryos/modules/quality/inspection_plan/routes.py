from factoryos.modules.quality.inspection_plan.models import *

from datetime import datetime
import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from extensions import db
from factoryos.modules.quality.inspection_plan.section_service import (
    add_section,
    delete_section,
    add_characteristic,
    update_characteristic_position,
    delete_characteristic
)
from factoryos.modules.quality.inspection_plan.marker_service import (
    create_marker,
    create_characteristic_with_marker,
    update_marker_position,
    delete_marker
)

from factoryos.modules.quality.inspection_plan.change_log_service import log_change

from factoryos.modules.quality.inspection_plan.revision_service import create_new_revision

from factoryos.modules.quality.inspection_plan.pdf_service import generate_inspection_plan_pdf

from factoryos.models.tools import ToolMasterdata
from factoryos.modules.quality.inspection_plan.feature_detection_service import detect_drawing_features

from factoryos.modules.quality.inspection_plan.image_service import (
    upload_identification_image,
    update_image_description,
    delete_identification_image
)

from factoryos.modules.quality.inspection_plan.drawing_service import (
    upload_drawing,
    upload_snippet,
    delete_snippet
)

inspection_bp = Blueprint(
    "inspection",
    __name__,
    url_prefix="/quality"
)

@inspection_bp.route("/")
@login_required
def quality_dashboard():
    return render_template("quality/dashboard.html")

@inspection_bp.route("/inspectionplan")
@login_required
def quality_inspection_plan():

    plans = (
        QualityInspectionPlan.query
        .order_by(QualityInspectionPlan.id.desc())
        .all()
    )

    return render_template(
        "qm_inspectionplan.html",
        plans=plans
    )

@inspection_bp.route("/create", methods=["GET", "POST"])
@login_required
def quality_create():

    tools = ToolMasterdata.query.order_by(ToolMasterdata.tool_no).all()

    if request.method == "POST":

        tool_id = request.form.get("tool_id")

        plan = QualityInspectionPlan(
            tool_id=tool_id,
            created_by_id=current_user.id
        )

        db.session.add(plan)
        db.session.flush()

        version = QualityInspectionPlanVersion(
            plan_id=plan.id,
            revision=1.0
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

    return render_template("qm_create.html", tools=tools)


@inspection_bp.route("/<int:plan_id>/version/<int:version_id>/edit", methods=["GET","POST"])
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

        # Modul hinzufügen
        add_type = request.form.get("add_section_type")

        if add_type and version.status == "draft":

            add_section(version, add_type)

            return redirect(request.url)

        # Freigabe
        if request.form.get("release_version"):

            if not version.is_dirty:
                return redirect(request.url)

            version.status = "released"
            version.released_at = datetime.utcnow()
            version.released_by_id = current_user.id
            version.is_dirty = False  # 👈 Reset


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

@inspection_bp.route("/<int:version_id>/new_revision", methods=["POST"])
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

@inspection_bp.route("/section/<int:section_id>/delete", methods=["POST"])
@login_required
def quality_delete_section(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)
    version = section.version

    if version.status != "draft":
        return redirect(request.referrer)

    title = section.title

    delete_section(section)

    return redirect(
        url_for(
            "inspection.quality_version_edit",
            plan_id=version.plan_id,
            version_id=version.id
        )
    )

@inspection_bp.route("/section/<int:section_id>/upload_image", methods=["POST"])
@login_required
def quality_upload_identification_image(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.section_type != "identification":
        return redirect(request.referrer)

    if section.version.status != "draft":
        return redirect(request.referrer)

    if len(section.images) >= 5:
        flash("Maximal 5 Bilder erlaubt.", "danger")
        return redirect(request.referrer)

    file = request.files.get("image")

    if not file:
        return redirect(request.referrer)

    upload_identification_image(
        section,
        file,
        request.form.get("description"),
        current_user.id
    )

    return redirect(request.referrer)

@inspection_bp.route("/image/<int:image_id>/update_description", methods=["POST"])
@login_required
def quality_update_image_description(image_id):

    image = QualityInspectionIdentificationImage.query.get_or_404(image_id)
    section = image.section

    if section.version.status != "draft":
        return redirect(request.referrer)
    
    new_description = request.form.get("description")

    update_image_description(image, new_description)

    return redirect(request.referrer)

@inspection_bp.route("/image/<int:image_id>/delete", methods=["POST"])
@login_required
def quality_delete_identification_image(image_id):

    image = QualityInspectionIdentificationImage.query.get_or_404(image_id)
    section = image.section

    if section.version.status != "draft":
        return redirect(request.referrer)

    delete_identification_image(image)

    return redirect(request.referrer)



@inspection_bp.route("/section/<int:section_id>/upload_drawing", methods=["POST"])
@login_required
def quality_upload_drawing(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    file = request.files.get("drawing")

    if not file:
        return redirect(request.referrer)

    upload_drawing(section, file)

    return redirect(request.referrer)

@inspection_bp.route("/section/<int:section_id>/upload_snippet", methods=["POST"])
@login_required
def quality_upload_snippet(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer)

    file = request.files.get("snippet")

    upload_snippet(
        section,
        file,
        request.form.get("description")
    )

    return redirect(request.referrer)

@inspection_bp.route("/snippet/<int:snippet_id>/delete", methods=["POST"])
@login_required
def quality_delete_snippet(snippet_id):

    snippet = QualityInspectionDimensionSnippet.query.get_or_404(snippet_id)

    delete_snippet(snippet)

    return redirect(request.referrer)

@inspection_bp.route("/section/<int:section_id>/add_characteristic", methods=["POST"])
@login_required
def quality_add_characteristic(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer)

    add_characteristic(section, request.form)

    return redirect(request.referrer)

@inspection_bp.route("/set_characteristic_position", methods=["POST"])
@login_required
def quality_set_characteristic_position():

    data = request.get_json()

    section = QualityInspectionSection.query.get_or_404(data["section_id"])

    if section.version.status != "draft":
        return jsonify({"error": "revision locked"}), 403

    characteristic = create_marker(
        data["section_id"],
        data["x"],
        data["y"]
    )

    return jsonify({"id": characteristic.id})


@inspection_bp.route("/update_characteristic_position", methods=["POST"])
@login_required
def quality_update_characteristic_position():

    char = db.session.get(QualityInspectionCharacteristic, data["id"])

    if char.section.version.status != "draft":
        return jsonify({"error": "revision locked"}), 403

    update_marker_position(
        data["id"],
        data["x"],
        data["y"]
    )

@inspection_bp.route("/delete_characteristic_marker", methods=["POST"])
@login_required
def quality_delete_characteristic_marker():

    data = request.json

    char = db.session.get(QualityInspectionCharacteristic, data.get("id"))

    if char.section.version.status != "draft":
        return jsonify({"error": "revision locked"}), 403

    delete_marker(char.id)

    return jsonify({"success": True})

@inspection_bp.route("/create_characteristic_with_marker", methods=["POST"])
@login_required
def quality_create_characteristic_with_marker():

    characteristic = create_characteristic_with_marker(
        request.json
    )

    return jsonify({
        "success": True,
        "id": characteristic.id
    })

@inspection_bp.route("/add_point", methods=["POST"])
@login_required
def quality_add_point():

    data = request.get_json()

    characteristic = create_marker(
        data.get("section_id"),
        data.get("pos_x"),
        data.get("pos_y")
    )

    return jsonify({
        "status": "ok",
        "id": characteristic.id
    })

@inspection_bp.route("/<int:plan_id>/delete", methods=["POST"])
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

@inspection_bp.route("/export_pdf/<int:version_id>")
@login_required
def quality_export_pdf(version_id):

    pdf_path = generate_inspection_plan_pdf(version_id)

    version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    version.pdf_path = pdf_path

    db.session.commit()

    return redirect(
        url_for(
            "inspection.quality_version_edit",
            plan_id=version.plan_id,
            version_id=version.id
        )
    )

@inspection_bp.route("/detect_features/<int:section_id>")
@login_required
def detect_features(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if not section.drawing_path:
        return jsonify([])
    
    img_path = os.path.join(
        current_app.static_folder,
        section.drawing_path
    )

    circles = detect_drawing_features(img_path)

    return jsonify(circles)

@inspection_bp.route("/section/<int:section_id>/add_gauge_check", methods=["POST"])
@login_required
def quality_add_gauge_check(section_id):

    section = QualityInspectionSection.query.get_or_404(section_id)

    if section.version.status != "draft":
        return redirect(request.referrer)
    
    last = (
        QualityInspectionGaugeCheck.query
        .filter_by(section_id=section.id)
        .order_by(QualityInspectionGaugeCheck.sort_order.desc())
        .first()
    )

    order = 1
    if last:
        order = last.sort_order + 1

    check = QualityInspectionGaugeCheck(

        section_id = section.id,
        name = request.form.get("name"),
        gauge_id = request.form.get("gauge_id"),
        method = request.form.get("method"),
        sort_order = order

    )

    db.session.add(check)

    section.version.is_dirty = True

    log_change(
        section.version,
        "ADD_GAUGE_CHECK",
        f"Lehrenprüfung '{check.name}' hinzugefügt"
    )

    db.session.commit()

    return redirect(request.referrer)
