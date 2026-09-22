from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.orders.models import Order
from factoryos.modules.production.services.machine_service import (
    close_all_active_bookings,
    start_machine_free
)


FINISHED_ORDER_STATUSES = ("fertig", "gesperrt", "finished", "locked")


def get_manual_start_data():
    machines = (
        Machine.query
        .filter(Machine.machine_status == "aktiv")
        .order_by(Machine.machine_no.asc(), Machine.name.asc())
        .all()
    )

    orders = (
        Order.query
        .filter(
            ~func.lower(func.coalesce(Order.status, "")).in_(FINISHED_ORDER_STATUSES)
        )
        .order_by(Order.order_no.asc())
        .all()
    )

    active_bookings = (
        TimeBooking.query
        .options(
            joinedload(TimeBooking.order),
            joinedload(TimeBooking.machine),
        )
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .all()
    )

    active_by_machine = {}
    active_by_order = {}
    for booking in active_bookings:
        if booking.machine_id and booking.machine_id not in active_by_machine:
            active_by_machine[booking.machine_id] = booking
        if booking.order_id and booking.order_id not in active_by_order:
            active_by_order[booking.order_id] = booking

    return {
        "machines": machines,
        "orders": orders,
        "active_by_machine": active_by_machine,
        "active_by_order": active_by_order,
    }


def start_production(user_id, order_id, machine_id, comment=None):

    order = Order.query.get_or_404(order_id)

    close_all_active_bookings(machine_id)

    if (order.status or "").lower() in ("open", "offen"):
        order.status = "in_arbeit"

    b = TimeBooking(
        user_id=user_id,
        order_id=order.id,
        machine_id=machine_id,
        type="START",
        process="PROD",
        tool_no=order.tool_no,
        comment=(comment or "").strip()[:255] or None,
        start_time=datetime.utcnow()
    )

    db.session.add(b)
    db.session.commit()

    return b


def end_booking(booking_id, user_id, action):

    booking = TimeBooking.query.get_or_404(booking_id)

    booking.end_time = datetime.utcnow()

    if action == "PAUSE":

        pause = TimeBooking(
            user_id=user_id,
            order_id=booking.order_id,
            machine_id=booking.machine_id,
            type="PAUSE",
            process="PAUSE",
            tool_no=booking.tool_no,
            start_time=datetime.utcnow()
        )

        db.session.add(pause)

    else:

        start_machine_free(booking.machine_id, user_id)

    db.session.commit()


def resume_booking(booking_id, user_id):

    booking = TimeBooking.query.get_or_404(booking_id)

    booking.end_time = datetime.utcnow()

    order = Order.query.get(booking.order_id)

    if order:

        new_start = TimeBooking(
            user_id=user_id,
            order_id=order.id,
            machine_id=booking.machine_id,
            type="START",
            process="PROD",
            tool_no=order.tool_no,
            start_time=datetime.utcnow()
        )

        db.session.add(new_start)

    db.session.commit()
