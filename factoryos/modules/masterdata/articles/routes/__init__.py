from flask import Blueprint

bp = Blueprint(
    "articles",
    __name__,
    url_prefix="/masterdata/articles"
)

from . import dashboard_routes
from . import list_routes
from . import create_routes
from . import edit_routes
from . import delete_routes

