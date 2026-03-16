from flask import Blueprint

bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/orders"
)

from .dashboard_routes import *
from .order_routes import *
from . import create_routes
from . import edit_routes
from . import delete_routes
