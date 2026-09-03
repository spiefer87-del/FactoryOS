from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    send_file,
    url_for,
)
from flask_login import current_user

from factoryos.core.storage import resolve_stored_file


bp = Blueprint("core", __name__)


@bp.route("/")
def home():

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    return render_template("dashboard/home.html")


@bp.route("/storage/<path:storage_path>")
def storage_file(storage_path):

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    try:
        file_path = resolve_stored_file(storage_path)
    except ValueError:
        abort(404)

    if not file_path.is_file():
        abort(404)

    return send_file(
        file_path,
        conditional=True,
    )
