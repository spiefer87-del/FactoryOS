from flask import Blueprint

bp = Blueprint(
    "orders",
    __name__,
    url_prefix="/orders"
)

from .dashboard_routes import *
from .overview_routes import *
from .detail_routes import  *
from .create_routes import * 
from .edit_routes import *
from .delete_routes import *
