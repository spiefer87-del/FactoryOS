from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, jsonify, abort
from factoryos.extensions import db, login_manager
from factoryos.models.user import User


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


def is_system_admin(user=None):
    user = user or current_user
    return bool(user.is_authenticated and user.active and user.role and user.role.active
                and (user.role.name or "").strip().casefold() == "admin")


def has_permission(user, permission_name):
    if not user or not user.is_authenticated or not user.active or not user.role or not user.role.active:
        return False
    if is_system_admin(user):
        return True
    return any(p.name == permission_name for p in user.role.permissions)


def role_required(*roles):
    allowed = {r.strip().casefold() for r in roles}
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.active or not current_user.role or not current_user.role.active:
                abort(403)
            if not is_system_admin(current_user) and (current_user.role.name or "").strip().casefold() not in allowed:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permission_required(permission_name, json_response=False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                if json_response:
                    return jsonify(success=False, error="Nicht angemeldet"), 401
                return redirect(url_for("auth.login"))
            if not has_permission(current_user, permission_name):
                if json_response:
                    return jsonify(success=False, error="Keine Berechtigung"), 403
                abort(403)
            return fn(*args, **kwargs)
        wrapper.required_permission = permission_name
        return wrapper
    return decorator
