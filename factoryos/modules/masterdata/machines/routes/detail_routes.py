from flask import (
    render_template,
    request
)

from flask_login import (
    login_required,
    current_user
)

from factoryos.core.auth import (
    permission_required,
    has_permission
)

from factoryos.core.queries.change_log_queries import (
    get_logs
)

from factoryos.modules.masterdata.shared.constants import (
    MACHINE_TYPES,
    MACHINE_STATUSES,
    MACHINE_STATUS_COLORS
)

from ..queries.machine_queries import get_machine

from . import bp


@bp.route("/<int:machine_id>")
@login_required
@permission_required("machines.view")
def detail(machine_id):

    machine = get_machine(
        machine_id
    )

    limit_param = request.args.get(
        "limit",
        "5"
    )

    if limit_param == "all":

        limit = None

    else:

        try:
            limit = int(limit_param)
        except ValueError:
            limit = 5

    logs = get_logs(
        entity_type="machine",
        entity_id=machine.id,
        limit=limit
    )

    return render_template(
        "masterdata/machines/detail.html",
        machine=machine,
        logs=logs,

        MACHINE_TYPES=MACHINE_TYPES,
        MACHINE_STATUSES=MACHINE_STATUSES,
        MACHINE_STATUS_COLORS=MACHINE_STATUS_COLORS,

        can_edit_machine=has_permission(
            current_user,
            "machines.edit"
        ),

        can_delete_machine=has_permission(
            current_user,
            "machines.delete"
        )
    )
