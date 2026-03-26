from flask import Blueprint

bp = Blueprint(
    "activity",
    __name__,
    url_prefix="/activity"
)

from .routes import activity_routes
