from flask import (
    redirect,
    url_for,
    flash
)

from flask_login import login_required

from factoryos.core.auth import permission_required

from ..queries.machine_queries import get_machine
from ..services.machine_service import delete_machine

from . import bp


@bp.route("/<int:machine_id>/delete", methods=["POST"])
@login_required
@permission_required("machines.delete")
def delete(machine_id):

    machine = get_machine(
        machine_id
    )

    delete_machine(
        machine
    )

    flash(
        "Maschine wurde gelöscht.",
        "success"
    )

    return redirect(
        url_for("machines.list_machines")
    )
