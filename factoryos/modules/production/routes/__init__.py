from flask import Blueprint

bp = Blueprint(
    "production",
    __name__,
    url_prefix="/production"
)

# Route Dateien importieren
from . import dashboard_routes
from . import booking_routes
from . import machine_routes
