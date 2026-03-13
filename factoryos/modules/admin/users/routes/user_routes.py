from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from factoryos.core.permissions import role_required

from factoryos.modules.admin.users.queries.user_queries import (
    get_all_users,
    get_user
)

from factoryos.modules.admin.users.services.user_service import (
    create_new_user,
    update_existing_user,
    remove_user
)


bp = Blueprint(
    "admin_users",
    __name__,
    url_prefix="/admin/users"
)


@bp.route("/")
@login_required
@role_required("admin")
def user_list():

    users = get_all_users()

    return render_template(
        "admin/users/user_list.html",
        users=users
    )


@bp.route("/create", methods=["GET","POST"])
@login_required
@role_required("admin")
def user_create():

    if request.method == "POST":

        try:
            create_new_user(request.form)

            flash("User erstellt", "success")

        except ValueError as e:

            flash(str(e), "danger")
            return redirect(url_for("admin_users.user_create"))

        return redirect(url_for("admin_users.user_list"))

    return render_template("admin/users/user_create.html")


@bp.route("/edit/<int:user_id>", methods=["GET","POST"])
@login_required
@role_required("admin")
def user_edit(user_id):

    user = get_user(user_id)

    if request.method == "POST":

        try:
            update_existing_user(user_id, request.form)

            flash("User gespeichert", "success")

        except ValueError as e:

            flash(str(e), "danger")
            return redirect(
                url_for("admin_users.user_edit", user_id=user_id)
            )

        return redirect(url_for("admin_users.user_list"))

    return render_template(
        "admin/users/user_edit.html",
        user=user
    )


@bp.route("/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def user_delete(user_id):

    remove_user(user_id)

    flash("User gelöscht", "success")

    return redirect(url_for("admin_users.user_list"))
