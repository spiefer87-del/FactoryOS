from flask import Blueprint

bp = Blueprint(
    "tools",
    __name__,
    url_prefix="/masterdata/tools"
)
