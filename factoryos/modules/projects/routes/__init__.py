from flask import Blueprint

bp = Blueprint(
    "projects",
    __name__,
    url_prefix="/projects"
)

# Route Dateien importieren
from . import workspace_routes
