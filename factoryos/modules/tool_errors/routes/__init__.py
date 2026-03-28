from flask import Blueprint

bp = Blueprint(
    "tool_error",
    __name__,
    url_prefix="/tool-errors"
)

# Route Dateien importieren
from tool_errors.routes import tool_error_routes
