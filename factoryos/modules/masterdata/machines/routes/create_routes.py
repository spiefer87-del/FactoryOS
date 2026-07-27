from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from sqlalchemy.exc import IntegrityError

from factoryos.extensions import db
from factoryos.core.auth import permission_required

from factoryos.modules.masterdata.shared.constants import (
    MACHINE_TYPES,
    MACHINE_STATUSES
)

from ..services.machine_service import create_machine

from . import bp


@bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("machines.create")
def create():

    if request.method == "POST":

        try:

            machine = create_machine(
                request.form,
                current_user.id
            )

            flash(
                "Maschine wurde angelegt.",
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
        "masterdata/machines/create.html",
        MACHINE_TYPES=MACHINE_TYPES,
        MACHINE_STATUSES=MACHINE_STATUSES
    )
