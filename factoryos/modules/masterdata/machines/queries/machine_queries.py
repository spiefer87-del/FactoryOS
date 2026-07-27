from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from factoryos.modules.masterdata.machines.models import (
    Machine,
    InjectionMoldingData
)


def get_machine(machine_id):

    return (
        Machine.query
        .options(
            joinedload(Machine.injection_molding_data),
            joinedload(Machine.created_by)
        )
        .filter(Machine.id == machine_id)
        .first_or_404()
    )


def get_machines(
    search="",
    status="",
    machine_type="",
    location=""
):

    query = (
        Machine.query
        .options(
            joinedload(Machine.injection_molding_data)
        )
    )

    if search:

        search_term = f"%{search}%"

        query = query.filter(
            or_(
                Machine.machine_no.ilike(search_term),
                Machine.external_machine_no.ilike(search_term),
                Machine.name.ilike(search_term),
                Machine.manufacturer.ilike(search_term),
                Machine.model.ilike(search_term),
                Machine.serial_no.ilike(search_term),
                Machine.location.ilike(search_term),
                Machine.description.ilike(search_term)
            )
        )

    if status:

        query = query.filter(
            Machine.machine_status == status
        )

    if machine_type:

        query = query.filter(
            Machine.machine_type == machine_type
        )

    if location:

        query = query.filter(
            Machine.location == location
        )

    return (
        query
        .order_by(
            Machine.machine_no.asc()
        )
        .all()
    )


def get_all_machines():

    return (
        Machine.query
        .order_by(Machine.machine_no.asc())
        .all()
    )
