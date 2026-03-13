from factoryos.modules.setup.machines.queries.machine_queries import (
    get_machine,
    create_machine,
    update_machine,
    delete_machine
)


def create_new_machine(form_data):

    if not form_data.get("name"):
        raise ValueError("Maschinenname fehlt")

    return create_machine(form_data)


def update_existing_machine(machine_id, form_data):

    machine = get_machine(machine_id)

    if not form_data.get("name"):
        raise ValueError("Maschinenname fehlt")

    return update_machine(machine, form_data)


def remove_machine(machine_id):

    machine = get_machine(machine_id)

    delete_machine(machine)
