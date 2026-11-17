from factoryos.core.services.change_log_service import record_entity, snapshot
from factoryos.core.services.change_log_service import log_change
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from .user_routes import bp


@bp.route("/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):

    user = User.query.get_or_404(user_id)

    roles = Role.query.filter_by(active=True).order_by(Role.name).all()

    if request.method == "POST":

        before=snapshot(user,("username","role_id","active"))
        username = request.form.get("username")
        role_id = request.form.get("role_id")
        active = request.form.get("active")

        user.username = username
        user.role_id = role_id
        user.active = True if active == "1" else False

        password = request.form.get("password")

        if password:
            user.set_password(password)

        record_entity(user,"user","update",("username","role_id","active"),before=before)
        if password:log_change("user",user.id,"password_change",{"password_changed":True},category="account",entity_name=user.username)
        db.session.commit()

        flash("Benutzer aktualisiert", "success")

        return redirect(url_for("admin_users.list_users"))

    return render_template(
        "admin/users/edit.html",
        user=user,
        roles=roles
    )