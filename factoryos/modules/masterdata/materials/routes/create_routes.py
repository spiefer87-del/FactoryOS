from flask import flash, redirect, render_template, request, url_for,abort
from types import SimpleNamespace
from factoryos.core.access_control import valid_csrf
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

from ..services.material_service import create_material,TEXT_FIELDS,FLOAT_FIELDS
from ..services.material_storage_service import (
    save_material_documents,
    validate_material_documents,
)
from . import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("materials.create")
def create():
    draft=None
    if request.method == "POST":
        if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
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
        values={key:request.form.get(key,"") for key in (*TEXT_FIELDS,*FLOAT_FIELDS)}
        values.update(material_type=values.get("material_type") or "plastic",base_unit=values.get("base_unit") or "kg",
            material_status=values.get("material_status") or "aktiv",hazardous_material=request.form.get("hazardous_material")=="1")
        draft=SimpleNamespace(**values)

    return render_template(
        "masterdata/materials/create.html",
        MATERIAL_TYPES=MATERIAL_TYPES,
        MATERIAL_STATUSES=MATERIAL_STATUSES,
        POLYMER_TYPES=POLYMER_TYPES,
        MATERIAL_BASE_UNITS=MATERIAL_BASE_UNITS,
        MATERIAL_DELIVERY_FORMS=MATERIAL_DELIVERY_FORMS,
        draft_material=draft,
    )
