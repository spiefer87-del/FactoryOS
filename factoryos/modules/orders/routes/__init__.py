from flask import Blueprint

bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/orders"
)

from .dashboard_routes import *