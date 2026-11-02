"""Central, fail-closed endpoint policy. Installed after blueprint registration."""
import secrets
from functools import wraps
from flask import request, session, abort, redirect, url_for, render_template
from flask_login import current_user
from .auth import has_permission, is_system_admin

READ = {
    "articles": {"dashboard", "list", "detail", "history"},
    "customers": {"overview", "detail"},
    "tools": {"dashboard", "list_tools", "detail", "search", "download_document"},
    "orders": {"dashboard", "overview", "detail"},
    "sampling": {"overview", "detail"},
    "production": {"dashboard", "booking_dashboard"},
    "projects": {"dashboard"},
    "quality": {"dashboard"},
    "quality_gauges": {"gauge_home", "gauge_detail"},
    "inspection": {"dashboard", "quality_inspection_plan", "tools_by_article"},
}
EXPLICIT = {
    "admin_users.list_users": "users.view", "admin_users.create_user": "users.create",
    "admin_users.edit_user": "users.edit", "admin_users.delete_user": "users.delete",
    "tools.image_primary": "tools.edit", "tools.upload_documents": "tools.documents", "tools.delete_document": "tools.documents",
    "production.manual_start": "production.start", "production.start_booking": "production.start",
    "production.resume_from_pause_or_downtime": "production.start", "production.end_booking_route": "production.stop",
    "production.machine_downtime": "production.stop", "production.machine_setup": "production.setup", "production.machine_event": "production.events",
    "production.booking_calendar_setup": "ADMIN", "production.delete_booking_calendar_exception": "ADMIN",
    "projects.projects_create": "projects.create", "projects.projects_start": "production.start", "projects.projects_stop": "production.stop",
    "sampling.complete": "sampling.release", "sampling.external_followup": "sampling.release", "sampling.stop_booking": "production.stop",
    "sampling.export_pdf": "sampling.pdf_export", "sampling.print_order": "sampling.pdf_export",
    "quality_gauges.gauge_new": "quality.inspect", "quality_gauges.gauge_calibration_new": "quality.inspect", "quality_gauges.gauge_update_status": "quality.inspect",
    "inspection.quality_export_pdf": "quality.pdf_export", "inspection.quality_export_section_drawing": "quality.pdf_export",
    "tool_error.get_image": "tool_error.view", "tool_error.set_tool_status_route": "tools.edit",
    "activity.list": "activity.view", "masterdata.dashboard": "LOGIN",
    "core.home": "LOGIN", "auth.logout": "LOGIN", "profile.settings": "LOGIN", "profile.change_password": "LOGIN", "profile.preferences": "LOGIN",
}
CONFIRM_GET = {
    "articles.delete", "orders.delete", "tools.delete", "tools.image_primary",
    "tool_error.start_review_route", "tool_error.return_to_draft_route", "tool_error.release_route",
    "tool_error.close_route", "tool_error.new_revision",
}
PROTECTED = set(READ) | {"machines", "materials", "tool_error", "activity", "admin", "admin_users", "admin_roles", "admin_permissions", "masterdata", "profile"}


def csrf_token():
    if "access_csrf" not in session:
        session["access_csrf"] = secrets.token_urlsafe(32)
    return session["access_csrf"]


def valid_csrf():
    token = request.form.get("access_csrf") or request.headers.get("X-Access-CSRF", "")
    expected = session.get("access_csrf", "")
    return bool(expected and isinstance(token, str) and secrets.compare_digest(expected, token))


def policy(endpoint, view=None):
    if endpoint in ("static", "core.storage_file", "auth.login"):
        return None
    if endpoint in EXPLICIT:
        return EXPLICIT[endpoint]
    blueprint, _, action = endpoint.partition(".")
    if blueprint in ("admin_roles", "admin_permissions"):
        return "ADMIN"
    if blueprint == "admin":
        return "ADMIN_MENU"
    permission = getattr(view, "required_permission", None)
    if permission:
        return permission
    if action in READ.get(blueprint, set()):
        return ("quality" if blueprint in ("quality_gauges", "inspection") else blueprint) + ".view"
    if blueprint in ("articles", "customers", "tools", "orders", "sampling") and action in ("create", "edit", "delete"):
        return blueprint + "." + action
    if blueprint == "inspection":
        return "quality.delete" if "delete" in action else "quality.inspect"
    return "DENY"


def allowed(spec, user=None):
    user = user or current_user
    if not user.is_authenticated or not user.active or (user.role and not user.role.active):
        return False
    if spec == "DENY":
        return False
    if spec == "LOGIN":
        return True
    if spec == "ADMIN":
        return is_system_admin(user)
    if spec == "ADMIN_MENU":
        return is_system_admin(user) or any(has_permission(user, "users." + a) for a in ("view", "create", "edit", "delete"))
    return has_permission(user, spec) if spec else True


def can_manage_user(target):
    if is_system_admin(current_user):
        return True
    if target.role and ((target.role.name or "").strip().casefold() == "admin" or not target.role.active):
        return False
    own = {p.name for p in current_user.role.permissions} if current_user.role else set()
    return not target.role or {p.name for p in target.role.permissions}.issubset(own)


def can_assign_role(role):
    if not role.active:
        return False
    if is_system_admin(current_user):
        return True
    own = {p.name for p in current_user.role.permissions} if current_user.role else set()
    return (role.name or "").strip().casefold() != "admin" and {p.name for p in role.permissions}.issubset(own)


def guard_admin_objects(endpoint):
    from factoryos.models.user import User
    from factoryos.modules.admin.roles.models import Role
    from sqlalchemy import func
    args = request.view_args or {}
    if endpoint.startswith("admin_users."):
        target = User.query.get_or_404(args["user_id"]) if "user_id" in args else None
        if target and not can_manage_user(target):
            abort(403, "Konten mit weitergehenden Rechten dürfen nicht verwaltet werden.")
        if request.method == "POST":
            if target and target.id == current_user.id:
                if request.form.get("password"):
                    abort(400, "Eigenes Passwort ausschließlich über das persönliche Profil ändern.")
                if endpoint.endswith("delete_user") or request.form.get("active") != "1" or request.form.get("role_id") != str(target.role_id):
                    abort(400, "Eigenes Administrationskonto nicht löschen, deaktivieren oder umstufen. Persönliches Passwort im Profil ändern.")
            if endpoint.endswith("delete_user") and target:
                from factoryos.extensions import db
                from sqlalchemy import select, inspect
                inspector = inspect(db.engine)
                existing_tables = set(inspector.get_table_names())
                for table in db.metadata.tables.values():
                    if table.name == "user_preferences" or table.name not in existing_tables:
                        continue
                    actual_columns = {c["name"] for c in inspector.get_columns(table.name)}
                    for column in table.columns:
                        if column.name in actual_columns and any(fk.target_fullname == "users.id" for fk in column.foreign_keys):
                            if db.session.execute(select(column).where(column == target.id).limit(1)).first():
                                abort(400, "Konto besitzt zugeordnete Vorgänge. Bitte deaktivieren statt löschen.")
            if endpoint.endswith(("create_user", "edit_user")):
                try:
                    role = Role.query.get_or_404(int(request.form.get("role_id", "")))
                except ValueError:
                    abort(400, "Eine gültige Rolle auswählen.")
                if not role.active:
                    abort(400, "Inaktive Rolle kann nicht zugewiesen werden.")
                if not is_system_admin(current_user):
                    own = {p.name for p in current_user.role.permissions}
                    if role.name.strip().casefold() == "admin" or not {p.name for p in role.permissions}.issubset(own):
                        abort(403, "Keine Vergabe weitergehender Rollenrechte.")
                username = request.form.get("username", "").strip()
                if not username or len(username) > 100 or username != request.form.get("username"):
                    abort(400, "Ungültiger Benutzername.")
                duplicate = User.query.filter(func.lower(User.username) == username.lower()).first()
                if duplicate and (not target or duplicate.id != target.id):
                    abort(400, "Benutzername bereits vorhanden.")
                if endpoint.endswith("create_user") and not request.form.get("password"):
                    abort(400, "Passwort erforderlich.")
                password = request.form.get("password", "")
                if password and (not 12 <= len(password) <= 128 or not password.strip()):
                    abort(400, "Neue Passwörter müssen 12 bis 128 Zeichen enthalten.")
    if endpoint.startswith("admin_roles.") and request.method == "POST":
        role = Role.query.get_or_404(args["role_id"]) if "role_id" in args else None
        if endpoint.endswith("delete_role_route"):
            if role.name.strip().casefold() == "admin" or User.query.filter_by(role_id=role.id).first():
                abort(400, "Systemrolle oder verwendete Rolle kann nicht gelöscht werden.")
        else:
            name = request.form.get("name", "").strip()
            if not name or len(name) > 50 or name != request.form.get("name"):
                abort(400, "Ungültiger Rollenname.")
            duplicate = Role.query.filter(func.lower(Role.name) == name.lower()).first()
            if duplicate and (not role or duplicate.id != role.id):
                abort(400, "Rollenname bereits vorhanden.")
            if role and role.name.strip().casefold() == "admin" and (name != role.name or request.form.get("active") != "1"):
                abort(400, "Systemrolle admin darf nicht umbenannt oder deaktiviert werden.")


def storage_permission(path):
    value = path.replace("\\", "/").casefold()
    if value.startswith(("uploads/tool_errors/", "stammdaten/werkzeuge/")) and ("werkzeugfehlermeldungen" in value or "tool_errors" in value):
        return "tool_error.view"
    if value.startswith(("uploads/tools/", "stammdaten/werkzeuge/")):
        return "tools.view"
    if value.startswith(("uploads/materials/", "stammdaten/materialien/")):
        return "materials.view"
    if value.startswith(("qm_drawings/", "qm_exports/", "qm_snippets/", "qm_identification/", "uploads/qm_drawings/", "uploads/qm_snippets/", "uploads/qm_identification/", "uploads/qm_exports/")):
        return "quality.view"
    return "ADMIN"


def install_access_control(app):
    @app.after_request
    def private_files(response):
        filename = (request.view_args or {}).get("filename", "")
        if request.endpoint == "core.storage_file" or (request.endpoint == "static" and filename.startswith(("uploads/", "qm_drawings/", "qm_exports/", "qm_snippets/", "qm_identification/"))):
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    @app.errorhandler(403)
    def forbidden(error):
        if request.is_json or request.path.startswith("/profile/preferences/"):
            return {"error": "Keine Berechtigung."}, 403
        return render_template("security/forbidden.html"), 403
    # Preserve old links as confirmation pages; the actual mutation becomes POST.
    for rule in list(app.url_map.iter_rules()):
        if rule.endpoint in CONFIRM_GET and "POST" not in rule.methods:
            app.add_url_rule(rule.rule, endpoint=rule.endpoint, view_func=app.view_functions[rule.endpoint], methods=["POST"])

    def can_access(endpoint):
        return allowed(policy(endpoint, app.view_functions.get(endpoint)))

    @app.context_processor
    def access_context():
        return {"can_access": can_access, "security_csrf_token": csrf_token,
                "can_manage_user": can_manage_user, "can_assign_role": can_assign_role, "is_system_admin": is_system_admin}

    @app.before_request
    def enforce_access():
        endpoint = request.endpoint
        if not endpoint or endpoint == "auth.login":
            return
        spec = policy(endpoint, app.view_functions.get(endpoint))
        if endpoint == "core.storage_file":
            spec = storage_permission((request.view_args or {}).get("storage_path", ""))
        if endpoint == "static":
            filename = (request.view_args or {}).get("filename", "")
            if filename.startswith(("uploads/", "qm_drawings/", "qm_exports/", "qm_snippets/", "qm_identification/")):
                spec = storage_permission(filename)
            else:
                return
        if spec is None:
            return
        if not current_user.is_authenticated:
            if endpoint == "profile.preferences":
                return {"error": "Bitte anmelden."}, 401
            return redirect(url_for("auth.login"))
        if endpoint == "auth.logout":
            return
        if not allowed(spec):
            abort(403, "Keine Berechtigung für diesen Bereich oder diese Aktion.")
        if endpoint == "admin_users.list_users" and request.method != "GET":
            abort(405)
        if endpoint == "admin_permissions.role_permissions":
            if request.method != "GET":
                abort(405)
            return redirect(url_for("admin_permissions.permission_matrix", _anchor="role-" + str(request.view_args["role_id"])))
        if endpoint.startswith("admin_"):
            if request.method == "POST" and not valid_csrf():
                abort(400, "Formular abgelaufen. Bitte neu laden.")
            guard_admin_objects(endpoint)
        if endpoint in CONFIRM_GET:
            if request.method in ("GET", "HEAD"):
                return render_template("security/confirm_action.html", action_url=request.path)
            if not valid_csrf():
                abort(400, "Formular abgelaufen. Bitte neu laden.")
