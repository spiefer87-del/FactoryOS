from flask import Blueprint

bp = Blueprint(
    "tools",
    __name__,
    url_prefix="/masterdata/tools"
)

from .dashboard_routes import *
from .list_routes import *
from .create_routes import *
from .edit_routes import *
from .delete_routes import *
from .detail_routes import *
from .search_routes import *
from .image_routes import *
from .import_routes import *
