from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from factoryos.core.auth import permission_required
from factoryos.extensions import db
from factoryos.modules.masterdata.shared.constants import (
    MATERIAL_BASE_UNITS,
    MATERIAL_DELIVERY_FORMS,
    MATERIAL_STATUSES,
    MATERIAL_TYPES,
    POLYMER_TYPES,
)

from ..services.material_service import create_material
from ..services.material_storage_service import (
    save_material_documents,
    validate_material_documents,
)
from . import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("materials.create")
def create():
    if request.method == "POST":
        try:
            uploads = {
                category: validate_material_documents(
                    request.files.getlist(category),
                    category,
                )
                for category in (
                    "data_sheets",
                    "safety_data_sheets",
                    "certificates",
                    "other",
                )
            }
            material = create_material(request.form, current_user.id)
            for category, files in uploads.items():
                save_material_documents(material, files, category)
            flash("Material wurde angelegt.", "success")
            return redirect(url_for("materials.detail", material_id=material.id))
        except IntegrityError:
            db.session.rollback()
            flash("Die Materialnummer existiert bereits.", "danger")
        except (OSError, TypeError, ValueError) as error:
            db.session.rollback()
            flash(f"Material konnte nicht angelegt werden: {error}", "danger")

    return render_template(
        "masterdata/materials/create.html",
        MATERIAL_TYPES=MATERIAL_TYPES,
        MATERIAL_STATUSES=MATERIAL_STATUSES,
        POLYMER_TYPES=POLYMER_TYPES,
        MATERIAL_BASE_UNITS=MATERIAL_BASE_UNITS,
        MATERIAL_DELIVERY_FORMS=MATERIAL_DELIVERY_FORMS,
    )
