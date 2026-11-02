import secrets
from flask import Blueprint, render_template, request, session, jsonify, flash, redirect, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from factoryos.extensions import db
from .service import DEFAULTS, all_preferences, save_preferences, PreferenceConflict

bp = Blueprint("profile", __name__, url_prefix="/profile")


@bp.after_app_request
def private_preferences(response):
    # Authenticated HTML embeds account-specific UI defaults and a CSRF token.
    if (request.endpoint or "").startswith("profile.") or (current_user.is_authenticated and response.mimetype == "text/html"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


def csrf_token():
    if "preferences_csrf" not in session:
        session["preferences_csrf"] = secrets.token_urlsafe(32)
    return session["preferences_csrf"]


def csrf_valid(value):
    expected = session.get("preferences_csrf", "")
    return bool(expected and isinstance(value, str) and secrets.compare_digest(expected, value))


@bp.app_context_processor
def preference_context():
    if not current_user.is_authenticated or not current_user.active:
        return {"ui_preferences_boot": None}
    return {"ui_preferences_boot": {"user_id": current_user.id, "csrf": csrf_token(),
            "url": url_for("profile.preferences", section="SECTION"),
            "sections": all_preferences(current_user.id)}}


@bp.route("/", methods=["GET", "POST"])
@login_required
def settings():
    if not current_user.active:
        return "Benutzer ist deaktiviert.", 403
    if request.method == "POST":
        if not csrf_valid(request.form.get("csrf_token")):
            return "Formular abgelaufen. Bitte neu laden.", 400
        try:
            action = request.form.get("action", "appearance")
            if action == "appearance":
                section = "appearance"
                values = {"density": request.form.get("density"), "accent": request.form.get("accent")}
            elif action in ("articles.columns", "tools.columns"):
                section, values = action, dict(DEFAULTS[action])
            else:
                raise ValueError("Ungültige Aktion.")
            save_preferences(current_user.id, section, values, int(request.form.get("version", "-1")))
        except (PreferenceConflict, IntegrityError, StaleDataError):
            db.session.rollback()
            flash("Einstellungen wurden in einem anderen Fenster geändert. Bitte erneut prüfen.", "warning")
            return redirect(url_for("profile.settings"))
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("profile.settings"))
        flash("Deine Einstellungen wurden im Benutzerkonto gespeichert.", "success")
        return redirect(url_for("profile.settings"))
    return render_template("profile/settings.html")


@bp.route("/password", methods=["POST"])
@login_required
def change_password():
    if not current_user.active:
        return "Benutzer ist deaktiviert.", 403
    if (not csrf_valid(request.form.get("csrf_token")) or
            request.form.get("account_id") != str(current_user.id)):
        return "Anmeldung oder Formular geändert. Bitte Profil neu laden.", 400
    from .password_service import change_own_password
    try:
        change_own_password(current_user._get_current_object(),
                            request.form.get("current_password", ""),
                            request.form.get("new_password", ""),
                            request.form.get("confirm_password", ""))
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("profile.settings", _anchor="password-settings"))
    logout_user()
    session.clear()
    session["_remember"] = "clear"
    flash("Passwort geändert. Bitte mit deinem neuen Passwort anmelden.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/preferences/<section>", methods=["GET", "PATCH"])
def preferences(section):
    if not current_user.is_authenticated:
        return jsonify(error="Bitte erneut anmelden."), 401
    if not current_user.active:
        return jsonify(error="Benutzer ist deaktiviert."), 403
    if section not in DEFAULTS:
        return jsonify(error="Unbekannter Einstellungsbereich."), 404
    if request.method == "GET":
        return jsonify(all_preferences(current_user.id)[section]), 200, {"Cache-Control": "private, no-store"}
    if (not csrf_valid(request.headers.get("X-CSRF-Token")) or
            request.headers.get("X-FactoryOS-User") != str(current_user.id)):
        return jsonify(error="Anmeldung oder Formular geändert. Bitte Seite neu laden."), 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {"values", "version"}:
        return jsonify(error="Ungültige Einstellungsdaten."), 400
    try:
        result = save_preferences(current_user.id, section, payload["values"], payload["version"])
    except (PreferenceConflict, IntegrityError, StaleDataError):
        db.session.rollback()
        return jsonify(error="Parallel geändert.", current=all_preferences(current_user.id)[section]), 409
    except ValueError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400
    return jsonify(result), 200, {"Cache-Control": "private, no-store"}
