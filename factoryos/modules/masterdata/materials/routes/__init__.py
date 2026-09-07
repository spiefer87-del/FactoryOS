from flask import Blueprint


bp = Blueprint(
    "materials",
    __name__,
    url_prefix="/masterdata/materials",
)


from .create_routes import *
from .dashboard_routes import *
from .delete_routes import *
from .detail_routes import *
from .document_routes import *
from .edit_routes import *
from .export_routes import *
from .import_routes import *
from .list_routes import *
