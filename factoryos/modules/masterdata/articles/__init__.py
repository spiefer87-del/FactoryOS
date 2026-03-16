from flask import Blueprint

bp = Blueprint(
    "articles",
    __name__,
    url_prefix="/masterdata/articles"
)

from .dashboard_routes import *
from .list_routes import *
from .create_routes import *
from .edit_routes import *
from .delete_routes import *
from .detail_routes import *
