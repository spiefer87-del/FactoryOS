from flask import Blueprint

bp = Blueprint(
    "activity",
    __name__,
    url_prefix="/activity"
)

from . import activity_routes
