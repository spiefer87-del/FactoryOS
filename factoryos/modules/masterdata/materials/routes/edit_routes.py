from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
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

from ..queries.material_queries import get_material
from ..services.material_service import update_material
from . import bp


@bp.route("/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("materials.edit")
def edit(material_id):
    material = get_material(material_id)
    if request.method == "POST":
        try:
            update_material(material, request.form)
            flash("Material wurde gespeichert.", "success")
            return redirect(url_for("materials.detail", material_id=material.id))
        except IntegrityError:
            db.session.rollback()
            flash("Die Materialnummer existiert bereits.", "danger")
        except (OSError, TypeError, ValueError) as error:
            db.session.rollback()
            flash(f"Material konnte nicht gespeichert werden: {error}", "danger")

    return render_template(
        "masterdata/materials/edit.html",
        material=material,
        MATERIAL_TYPES=MATERIAL_TYPES,
        MATERIAL_STATUSES=MATERIAL_STATUSES,
        POLYMER_TYPES=POLYMER_TYPES,
        MATERIAL_BASE_UNITS=MATERIAL_BASE_UNITS,
        MATERIAL_DELIVERY_FORMS=MATERIAL_DELIVERY_FORMS,
    )
