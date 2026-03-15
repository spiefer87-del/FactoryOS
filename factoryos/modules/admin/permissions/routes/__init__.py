from flask import Blueprint

bp = Blueprint(
    "admin_permissions",
    __name__,
    url_prefix="/admin/permissions"
)

from .role_permissions_routes import *
from .permission_matrix_routes import *
