from datetime import datetime

from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking, Order
from factoryos.modules.production.services import (
    close_all_active_bookings,
    start_machine_free
)


def start_production(user_id, order_id, machine_id):

    order = Order.query.get_or_404(order_id)

    close_all_active_bookings(machine_id)

    if order.status == "offen":
        order.status = "in_arbeit"

    b = TimeBooking(
        user_id=user_id,
        order_id=order.id,
        machine_id=machine_id,
        type="START",
        process="PROD",
        tool_no=order.tool_no,
        start_time=datetime.utcnow()
    )

    db.session.add(b)
    db.session.commit()


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
