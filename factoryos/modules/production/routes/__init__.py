from flask import Blueprint


bp = Blueprint(
    "production",
    __name__,
    url_prefix="/production",
)


# Route Dateien importieren
from . import booking_routes
from . import calendar_routes
from . import dashboard_routes
from . import machine_routes
from factoryos.modules.tool_errors.routes import tool_error_routes
