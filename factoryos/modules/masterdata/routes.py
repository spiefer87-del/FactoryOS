from flask import Blueprint, render_template
from flask_login import login_required

from factoryos.modules.masterdata.core.registry import list_masterdata


masterdata_bp = Blueprint(
    "masterdata",
    __name__,
    url_prefix="/masterdata"
)


@masterdata_bp.route("/")
@login_required
def masterdata_home():

    modules = list_masterdata()

    return render_template(
        "masterdata/index.html",
        modules=modules
    )
