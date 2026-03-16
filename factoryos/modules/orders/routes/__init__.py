from flask import Blueprint

bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/orders"
)

from . import dashboard_routes
from . import overview_routes
from . import detail_routes
from . import create_routes
from . import edit_routes
from . import delete_routes
