from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.modules.setup.machines.queries.machine_queries import (
    get_all_machines,
    get_machine
)

from factoryos.modules.setup.machines.services.machine_service import (
    create_new_machine,
    update_existing_machine,
    remove_machine
)

from factoryos.core.permissions import role_required


bp = Blueprint(
    "setup_machines",
    __name__,
    url_prefix="/setup/machines"
)


@bp.route("/")
@login_required
@role_required("admin")
def machine_list():

    machines = get_all_machines()

    return render_template(
        "setup/machines/machine_list.html",
        machines=machines
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@role_required("admin")
def machine_create():

    if request.method == "POST":

        try:
            create_new_machine(request.form)
            flash("Maschine erstellt.", "success")

        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("setup_machines.machine_create"))

        return redirect(url_for("setup_machines.machine_list"))

    return render_template("setup/machines/machine_create.html")


@bp.route("/edit/<int:machine_id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def machine_edit(machine_id):

    machine = get_machine(machine_id)

    if request.method == "POST":

        try:
            update_existing_machine(machine_id, request.form)
            flash("Maschine gespeichert.", "success")

        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("setup_machines.machine_edit", machine_id=machine_id))

        return redirect(url_for("setup_machines.machine_list"))

    return render_template(
        "setup/machines/machine_edit.html",
        machine=machine
    )


@bp.route("/delete/<int:machine_id>", methods=["POST"])
@login_required
@role_required("admin")
def machine_delete(machine_id):

    remove_machine(machine_id)

    flash("Maschine gelöscht.", "success")

    return redirect(url_for("setup_machines.machine_list"))
