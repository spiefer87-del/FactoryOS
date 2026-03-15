from datetime import datetime

from factoryos.extensions import db
from factoryos.modules.production.models import TimeBooking


# --------------------------------------------------
# Alle aktiven Buchungen schließen
# --------------------------------------------------

def close_all_active_bookings(machine_id):

    bookings = (
        TimeBooking.query
        .filter_by(machine_id=machine_id)
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    now = datetime.utcnow()

    for b in bookings:
        b.end_time = now

    db.session.flush()

    return bookings


# --------------------------------------------------
# Maschine auf FREI setzen
# --------------------------------------------------

def start_machine_free(machine_id, user_id):

    free = TimeBooking(
        user_id=user_id,
        machine_id=machine_id,
        order_id=None,
        type="START",
        process="FREI",
        tool_no=None,
        start_time=datetime.utcnow()
    )

    db.session.add(free)

    db.session.flush()

    return free


# --------------------------------------------------
# Setup starten (RUEST / ABRUEST)
# --------------------------------------------------

def start_setup(machine_id, user_id, tool_no, order_id=None, mode="RUEST", comment=None):

    close_all_active_bookings(machine_id)

    booking = TimeBooking(
        user_id=user_id,
        machine_id=machine_id,
        order_id=order_id,
        type="START",
        process=mode,
        tool_no=tool_no,
        comment=comment,
        start_time=datetime.utcnow()
    )

    db.session.add(booking)

    db.session.flush()

    return booking


# --------------------------------------------------
# Maschinen Event starten
# --------------------------------------------------

def start_machine_event(machine_id, user_id, event, comment=None):

    close_all_active_bookings(machine_id)

    booking = TimeBooking(
        user_id=user_id,
        machine_id=machine_id,
        order_id=None,
        type="START",
        process=event,
        tool_no=None,
        comment=comment,
        start_time=datetime.utcnow()
    )

    db.session.add(booking)

    db.session.flush()

    return booking


# --------------------------------------------------
# Maschinenstatus abrufen
# --------------------------------------------------

def get_active_machine_state(machine_id):

    booking = (
        TimeBooking.query
        .filter_by(machine_id=machine_id)
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .first()
    )

    if not booking:
        return {
            "status": "FREI",
            "booking": None
        }

    return {
        "status": booking.process,
        "booking": booking
    }

def start_machine_downtime(machine_id, user_id, reason_id=None, comment=None, prev_order_id=None, tool_no=None):

    close_all_active_bookings(machine_id)

    booking = TimeBooking(
        user_id=user_id,
        machine_id=machine_id,
        order_id=None,
        prev_order_id=prev_order_id,
        type="START",
        process="STOERUNG",
        tool_no=tool_no,
        downtime_reason_id=reason_id,
        comment=comment,
        start_time=datetime.utcnow()
    )

    db.session.add(booking)
    db.session.flush()

    return booking