from flask import render_template
from flask_login import login_required, current_user

from factoryos.core.auth import (
    permission_required,
    has_permission
)

from factoryos.modules.masterdata.shared.constants import (
    MACHINE_TYPES,
    MACHINE_STATUSES,
    MACHINE_STATUS_COLORS
)

from ..queries.machine_queries import get_machines

from . import bp


@bp.route("/list")
@login_required
@permission_required("machines.view")
def list_machines():

    machines = get_machines()

    return render_template(
        "masterdata/machines/list.html",
        machines=machines,

        MACHINE_TYPES=MACHINE_TYPES,
        MACHINE_STATUSES=MACHINE_STATUSES,
        MACHINE_STATUS_COLORS=MACHINE_STATUS_COLORS,

        can_create_machine=has_permission(
            current_user,
            "machines.create"
        ),

        can_edit_machines=has_permission(
            current_user,
            "machines.edit"
        ),

        can_delete_machines=has_permission(
            current_user,
            "machines.delete"
        )
    )
