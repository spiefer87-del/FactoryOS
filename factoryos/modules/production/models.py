from datetime import datetime, timedelta
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool


class DowntimeReason(db.Model):
    __tablename__ = "downtime_reasons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class TimeBooking(db.Model):
    __tablename__ = "time_bookings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=True)
    process = db.Column(db.String(20), default="PROD")  # PROD, RUEST, ABRUEST
    tool_no = db.Column(db.String(50), nullable=True)


    # START, PAUSE, STOP, STOERUNG
    type = db.Column(db.String(20), nullable=False)

    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)  # NULL = aktiv
    prev_order_id = db.Column(db.Integer, nullable=True)

    comment = db.Column(db.String(255), nullable=True)

    downtime_reason_id = db.Column(db.Integer, db.ForeignKey("downtime_reasons.id"), nullable=True)

    user = db.relationship("User", backref="bookings")
    order = db.relationship("Order", backref="bookings")
    machine = db.relationship("Machine", backref="bookings")
    downtime_reason = db.relationship("DowntimeReason", backref="bookings")

    @property
    def is_active(self):
        return self.end_time is None

class QuantityReport(db.Model):
    __tablename__ = "quantity_reports"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)

    good_qty = db.Column(db.Integer, default=0)
    scrap_qty = db.Column(db.Integer, default=0)

    note = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="qty_reports")
    order = db.relationship("Order", backref="qty_reports")
    machine = db.relationship("Machine", backref="qty_reports")


class ProductionCalendarSettings(db.Model):
    """Weekly production window used by machine-booking forecasts."""

    __tablename__ = "production_calendar_settings"

    id = db.Column(db.Integer, primary_key=True)
    week_start_day = db.Column(db.Integer, nullable=False, default=0)
    week_start_time = db.Column(db.String(5), nullable=False, default="04:30")
    week_end_day = db.Column(db.Integer, nullable=False, default=5)
    week_end_time = db.Column(db.String(5), nullable=False, default="06:00")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ProductionCalendarException(db.Model):
    """Non-production period such as a holiday or bridge day."""

    __tablename__ = "production_calendar_exceptions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    start_at = db.Column(db.DateTime, nullable=False, index=True)
    end_at = db.Column(db.DateTime, nullable=False, index=True)
    all_day = db.Column(db.Boolean, nullable=False, default=True)
    note = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User")

    @property
    def display_end_date(self):
        if self.all_day:
            return (self.end_at - timedelta(microseconds=1)).date()
        return self.end_at.date()


