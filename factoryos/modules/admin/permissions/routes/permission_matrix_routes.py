import hashlib
import json
import secrets
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required
from factoryos.extensions import db
from factoryos.core.auth import role_required
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from . import bp


def revision(roles):
    state = [(r.id, r.name, r.active, sorted(p.id for p in r.permissions)) for r in roles]
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


@bp.route("/matrix", methods=["GET", "POST"])
@login_required
@role_required("admin")
def permission_matrix():
    roles = Role.query.order_by(Role.name).all()
    permissions = Permission.query.order_by(Permission.name).all()
    permission_groups = {}
    for permission in permissions:
        permission_groups.setdefault(permission.name.split(".", 1)[0], []).append(permission)
    current_revision = revision(roles)
    if request.method == "POST":
        if not secrets.compare_digest(request.form.get("permissions_revision", ""), current_revision):
            abort(409, "Rechte wurden zwischenzeitlich geändert. Bitte die Matrix neu laden.")
        known = {p.id: p for p in permissions}
        try:
            selected = {r.id: {int(x) for x in request.form.getlist(f"role_{r.id}")} for r in roles}
        except ValueError:
            abort(400, "Ungültige Rechteauswahl.")
        if any(ids - set(known) for ids in selected.values()):
            abort(400, "Unbekanntes Recht.")
        for role in roles:
            if role.name.strip().casefold() == "admin":
                continue
            before = sorted(p.id for p in role.permissions)
            role.permissions = [known[key] for key in sorted(selected[role.id])]
            after = sorted(selected[role.id])
            if before != after:
                log_change("role", role.id, "permissions_update", entity_name=role.name,
                           category="admin", changes={"permission_ids": {"old": before, "new": after}})
        db.session.commit()
        flash("Rechte aktualisiert. Systemadministratoren behalten den geschützten Vollzugriff.", "success")
        return redirect(url_for("admin_permissions.permission_matrix"))
    return render_template("admin/permissions/matrix.html", roles=roles,
                           permission_groups=dict(sorted(permission_groups.items())),
                           permissions_revision=current_revision)
