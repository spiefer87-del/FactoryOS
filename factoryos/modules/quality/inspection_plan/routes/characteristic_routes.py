from flask import request, jsonify, redirect, url_for
from flask_login import login_required

from factoryos.extensions import db
from ..models import QualityInspectionCharacteristic

from factoryos.modules.quality.inspection_plan.services.marker_service import (
    create_marker,
    create_characteristic_with_marker,
    update_marker_position,
    delete_marker,
    update_marker_rotation
)

from . import bp


@bp.route("/set_characteristic_position", methods=["POST"])
@login_required
def quality_set_characteristic_position():

    data = request.get_json()

    characteristic = create_marker(
        data["section_id"],
        data["x"],
        data["y"]
    )

    return jsonify({"id": characteristic.id})


@bp.route("/update_characteristic_position", methods=["POST"])
@login_required
def quality_update_characteristic_position():

    data = request.get_json()

    char = db.session.get(QualityInspectionCharacteristic, data["id"])

    if char.section.version.status != "draft":
        return jsonify({"error": "revision locked"}), 403

    update_marker_position(
        data["id"],
        data["x"],
        data["y"]
    )

    return jsonify({"success": True})


@bp.route("/delete_characteristic_marker", methods=["POST"])
@login_required
def quality_delete_characteristic_marker():

    data = request.get_json()

    char = db.session.get(QualityInspectionCharacteristic, data.get("id"))

    if char.section.version.status != "draft":
        return jsonify({"error": "revision locked"}), 403

    delete_marker(char.id)

    return jsonify({"success": True})


@bp.route("/create_characteristic_with_marker", methods=["POST"])
@login_required
def quality_create_characteristic_with_marker():

    data = request.json if request.is_json else request.form

    characteristic = create_characteristic_with_marker(data)

    # ==========================================
    # NORMALER FORM SUBMIT
    # ==========================================

    if not request.is_json:

        section = characteristic.section
        version = section.version

        return redirect(
            url_for(
                "inspection.quality_version_edit",
                plan_id=version.plan_id,
                version_id=version.id
            )
        )

    # ==========================================
    # AJAX RETURN
    # ==========================================

    return jsonify({

        "success": True,

        "id": characteristic.id,

        "number": characteristic.sort_order,

        "pos_x": characteristic.pos_x,

        "pos_y": characteristic.pos_y,

        "section_id": characteristic.section_id
    })

@bp.route("/add_point", methods=["POST"])
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
        "id": characteristic.id,
        "number": characteristic.sort_order
    })

@bp.route("/rotate_characteristic_marker", methods=["POST"])
@login_required
def quality_rotate_characteristic_marker():

    data = request.get_json()

    char = db.session.get(
        QualityInspectionCharacteristic,
        data["id"]
    )

    if not char:
        return jsonify({
            "error": "marker not found"
        }), 404

    if char.section.version.status != "draft":
        return jsonify({
            "error": "revision locked"
        }), 403

    update_marker_rotation(
        data["id"],
        data["rotation"]
    )

    return jsonify({
        "success": True
    })
