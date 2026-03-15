from flask import Blueprint

bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/projects"
)

# Route Dateien importieren
from . import dashboard_routes
from . import booking_routes
from . import project_routes
