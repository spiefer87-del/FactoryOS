from factoryos.extensions import db
from factoryos.models.machine import Machine


def get_all_machines():
    return (
        Machine.query
        .order_by(Machine.name.asc())
        .all()
    )


def get_machine(machine_id):
    return Machine.query.get_or_404(machine_id)


def create_machine(data):

    machine = Machine(
        name=data.get("name"),
        location=data.get("location"),
        active=True
    )

    db.session.add(machine)
    db.session.commit()

    return machine


def update_machine(machine, data):

    machine.name = data.get("name")
    machine.location = data.get("location")
    machine.active = data.get("active") == "on"

    db.session.commit()

    return machine


def delete_machine(machine):

    db.session.delete(machine)
    db.session.commit()
