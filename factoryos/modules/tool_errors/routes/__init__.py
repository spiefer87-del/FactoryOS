from flask import Blueprint

bp = Blueprint(
    "tool_error",
    __name__,
    url_prefix="/tool-errors"
)

# Route Dateien importieren
from .tool_error_routes import *
from .import_routes import *
from .export_routes import *
