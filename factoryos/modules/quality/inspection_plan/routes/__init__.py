from flask import Blueprint

bp = Blueprint(
    "inspection",
    __name__,
    url_prefix="/quality/inspection-plans"
)

# Route-Dateien laden
from .dashboard_routes import *
from .plan_routes import *
from .version_routes import *
from .section_routes import *
from .characteristic_routes import *
from .image_routes import *
from .drawing_routes import *
from .gauge_routes import *
from .pdf_routes import *
