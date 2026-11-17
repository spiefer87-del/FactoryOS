from factoryos.core.services.change_log_service import record_entity, snapshot
from flask import redirect, url_for, flash
from flask_login import login_required
from factoryos.extensions import db
from factoryos.models.user import User

from .user_routes import bp


@bp.route("/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    record_entity(user,"user","delete",("username","role_id","active"))
    db.session.delete(user)
    db.session.commit()

    flash("Benutzer gelöscht", "success")

    return redirect(url_for("admin_users.list_users"))