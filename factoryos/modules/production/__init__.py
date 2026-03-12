from .dashboard_routes import bp as dashboard_bp
from .booking_routes import bp as booking_bp
from .machine_routes import bp as machine_bp
from .order_routes import bp as order_bp

blueprints = [
    dashboard_bp,
    booking_bp,
    machine_bp,
    order_bp
]
