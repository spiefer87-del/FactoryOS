from sqlalchemy import func

from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking, QuantityReport, DowntimeReason


def get_dashboard_data():

    machines = (
        Machine.query
        .filter_by(active=True)
        .order_by(Machine.name.asc())
        .all()
    )

    active_bookings = (
        TimeBooking.query
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    active_by_machine = {}

    for b in active_bookings:

        if b.machine_id not in active_by_machine:
            active_by_machine[b.machine_id] = b
        else:
            if b.start_time > active_by_machine[b.machine_id].start_time:
                active_by_machine[b.machine_id] = b

    reasons = (
        DowntimeReason.query
        .filter_by(active=True)
        .order_by(DowntimeReason.name.asc())
        .all()
    )

    qty_sums = (
        db.session.query(
            QuantityReport.order_id,
            func.coalesce(func.sum(QuantityReport.good_qty), 0).label("good_sum"),
            func.coalesce(func.sum(QuantityReport.scrap_qty), 0).label("scrap_sum"),
        )
        .group_by(QuantityReport.order_id)
        .all()
    )

    qty_by_order = {
        row.order_id: {
            "good": row.good_sum,
            "scrap": row.scrap_sum
        }
        for row in qty_sums
    }

    return machines, active_by_machine, qty_by_order, reasons
