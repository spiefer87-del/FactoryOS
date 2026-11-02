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

    from factoryos.modules.sampling.models import SamplingOrder
    from factoryos.modules.production.models import TimeBooking,MachineControlState,MachineControlCommand,ProductionPlanEntry,MachinePlanningSettings
    from factoryos.modules.production.services.machine_control_service import acquire_control_lock
    from factoryos.extensions import db
    acquire_control_lock()
    if (TimeBooking.query.filter_by(machine_id=machine.id).first() or
        MachineControlState.query.filter_by(machine_id=machine.id).first() or
        MachineControlCommand.query.filter_by(machine_id=machine.id).first() or ProductionPlanEntry.query.filter_by(machine_id=machine.id).first() or db.session.get(MachinePlanningSettings,machine.id)):
        db.session.rollback()
        flash("Maschine besitzt Buchungen oder ein Bedienprotokoll. Bitte deaktivieren statt löschen.","warning")
        return redirect(url_for("machines.detail",machine_id=machine.id))
    if SamplingOrder.query.filter_by(machine_id=machine.id).first():
        db.session.rollback()
        flash("Dieser Stammdatensatz wird von einem Musterungsauftrag verwendet und kann nicht gelöscht werden.", "warning")
        return redirect(url_for("machines.detail", machine_id=machine.id))
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
