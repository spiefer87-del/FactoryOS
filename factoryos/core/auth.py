from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash
from factoryos.extensions import db, login_manager
from factoryos.models.user import User


@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))


def role_required(*roles):

    def decorator(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            if not current_user.role:
                flash("Keine Rolle zugewiesen.", "danger")
                return redirect(url_for("core.home"))

            # Admin darf alles
            if current_user.role.name == "admin":
                return fn(*args, **kwargs)

            if current_user.role.name not in roles:
                flash("Keine Berechtigung.", "danger")
                return redirect(url_for("core.home"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator
