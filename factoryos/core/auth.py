from functools import wraps

from flask_login import current_user
from flask import redirect, url_for, flash, request, jsonify

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

            if current_user.role.name.lower() == "admin":
                return fn(*args, **kwargs)

            if current_user.role.name not in roles:
                flash("Keine Berechtigung.", "danger")
                return redirect(url_for("core.home"))

            return fn(*args, **kwargs)

        return wrapper

    return decorator


# =========================
# PERMISSION SYSTEM
# =========================

def has_permission(user, permission_name):

    if not user or not user.is_authenticated:
        return False

    if not getattr(user, "active", True):
        return False

    if not user.role:
        return False

    # Admin darf alles
    #if user.role.name.lower() == "admin":
        #return True

    return any(
        permission.name == permission_name
        for permission in user.role.permissions
    )


def permission_required(permission_name, json_response=False):

    def decorator(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):

            if not current_user.is_authenticated:

                if json_response:
                    return jsonify({
                        "success": False,
                        "error": "Nicht angemeldet"
                    }), 401

                return redirect(url_for("auth.login"))

            if not has_permission(current_user, permission_name):

                if json_response:
                    return jsonify({
                        "success": False,
                        "error": "Keine Berechtigung"
                    }), 403

                flash("Keine Berechtigung für diese Aktion.", "danger")

                return redirect(
                    request.referrer or url_for("core.home")
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
