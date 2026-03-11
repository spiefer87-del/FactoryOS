from datetime import datetime

from extensions import db
from factoryos.modules.production.models import TimeBooking


# --------------------------------------------------
# Hilfsfunktion
# --------------------------------------------------

def close_all_active_bookings(machine_id: int):
    """
    Beendet ALLE aktiven Buchungen einer Maschine.
    Garantiert: Danach existiert keine end_time NULL mehr.
    """

    active_bookings = (
        TimeBooking.query
        .filter_by(machine_id=machine_id)
        .filter(TimeBooking.end_time.is_(None))
        .all()
    )

    now = datetime.utcnow()

    for b in active_bookings:
        b.end_time = now

    db.session.flush()


# --------------------------------------------------
# Maschinenstatus
# --------------------------------------------------

def get_active_machine_state(machine_id: int):

    booking = (
        TimeBooking.query
        .filter_by(machine_id=machine_id)
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .first()
    )

    if not booking:
        return {
            "booking": None,
            "is_free": True,
            "is_busy": False,
            "process": None
        }

    if booking.process == "FREI":
        return {
            "booking": booking,
            "is_free": True,
            "is_busy": False,
            "process": "FREI"
        }

    return {
        "booking": booking,
        "is_free": False,
        "is_busy": True,
        "process": booking.process
    }


# --------------------------------------------------
# Maschine FREI
# --------------------------------------------------

def start_machine_free(machine_id: int, user_id: int):

    close_all_active_bookings(machine_id)

    booking = TimeBooking(
        user_id=user_id,
        order_id=None,
        machine_id=machine_id,
        type="START",
        process="FREI",
        tool_no=None,
        start_time=datetime.utcnow()
    )

    db.session.add(booking)
    db.session.flush()

    return booking


# --------------------------------------------------
# Produktion starten
# --------------------------------------------------

def start_machine_production(
    machine_id: int,
    user_id: int,
    order_id: int,
    process: str,
    tool_no: str = None
):

    close_all_active_bookings(machine_id)

    booking = TimeBooking(
        user_id=user_id,
        order_id=order_id,
        machine_id=machine_id,
        type="START",
        process=process,
        tool_no=tool_no,
        start_time=datetime.utcnow()
    )

    db.session.add(booking)
    db.session.flush()

    return booking


# --------------------------------------------------
# Maschine stoppen
# --------------------------------------------------

def stop_machine(machine_id: int):

    booking = (
        TimeBooking.query
        .filter_by(machine_id=machine_id)
        .filter(TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time.desc())
        .first()
    )

    if not booking:
        return None

    booking.end_time = datetime.utcnow()

    db.session.flush()

    return booking