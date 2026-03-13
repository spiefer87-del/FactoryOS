from flask import request, jsonify
from flask_login import login_required

from factoryos.extensions import db
from factoryos.modules.quality.inspection_plan.models import QualityInspectionCharacteristic

from factoryos.modules.quality.inspection_plan.marker_service import (
    create_marker,
    create_characteristic_with_marker,
    update_marker_position,
    delete_marker
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

    characteristic = create_characteristic_with_marker(
        request.json
    )

    return jsonify({
        "success": True,
        "id": characteristic.id
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
        "id": characteristic.id
    })
