from flask import Blueprint

bp = Blueprint(
    "masterdata",
    __name__,
    url_prefix="/masterdata"
)

from .dashboard_routes import *
