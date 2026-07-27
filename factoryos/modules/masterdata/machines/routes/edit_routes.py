from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from factoryos.extensions import db
from factoryos.core.auth import permission_required

from factoryos.modules.masterdata.shared.constants import (
    MACHINE_TYPES,
    MACHINE_STATUSES
)

from ..queries.machine_queries import get_machine
from ..services.machine_service import update_machine

from . import bp


@bp.route("/<int:machine_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("machines.edit")
def edit(machine_id):

    machine = get_machine(
        machine_id
    )

    if request.method == "POST":

        try:

            update_machine(
                machine,
                request.form
            )

            flash(
                "Maschine wurde gespeichert.",
                "success"
            )

            return redirect(
                url_for(
                    "machines.detail",
                    machine_id=machine.id
                )
            )

        except IntegrityError:

            db.session.rollback()

            flash(
                "Die Maschinennummer existiert bereits.",
                "danger"
            )

        except (TypeError, ValueError) as error:

            db.session.rollback()

            flash(
                f"Ungültige Eingabe: {error}",
                "danger"
            )

    return render_template(
        "masterdata/machines/edit.html",
        machine=machine,
        MACHINE_TYPES=MACHINE_TYPES,
        MACHINE_STATUSES=MACHINE_STATUSES
    )
