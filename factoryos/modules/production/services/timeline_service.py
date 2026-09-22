from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.production.models import QuantityReport, TimeBooking


HORIZONS = {
    "24h": {
        "label": "24 Stunden",
        "past": timedelta(hours=6),
        "future": timedelta(hours=18),
        "tick": timedelta(hours=2),
    },
    "3d": {
        "label": "3 Tage",
        "past": timedelta(hours=18),
        "future": timedelta(hours=54),
        "tick": timedelta(hours=6),
    },
    "7d": {
        "label": "7 Tage",
        "past": timedelta(days=1),
        "future": timedelta(days=6),
        "tick": timedelta(hours=12),
    },
}

PROCESS_META = {
    "PROD": ("Produktion", "production"),
    "RUEST": ("Rüsten", "setup"),
    "ABRUEST": ("Abrüsten", "setup"),
    "STOERUNG": ("Störung", "downtime"),
    "PAUSE": ("Pause", "pause"),
    "FREI": ("Frei", "free"),
}


def _percent(moment, range_start, range_end):
    duration = (range_end - range_start).total_seconds()
    if duration <= 0:
        return 0.0
    return max(0.0, min(100.0, (moment - range_start).total_seconds() / duration * 100.0))


def _format_duration(seconds):
    minutes = max(0, int(round(seconds / 60)))
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if days:
        parts.append(f"{days} T")
    if hours:
        parts.append(f"{hours} Std")
    if minutes or not parts:
        parts.append(f"{minutes} Min")
    return " ".join(parts)


def _booking_label(booking, process_label):
    if booking.order:
        return booking.order.order_no
    if booking.process == "STOERUNG" and booking.downtime_reason:
        return booking.downtime_reason.name
    return process_label


def _forecast_for(booking, good_by_order, articles_by_number, now):
    if booking.process != "PROD" or not booking.order:
        return None

    order = booking.order
    article = articles_by_number.get((order.article or "").strip())
    if not article or not article.cycle_time_s or article.cycle_time_s <= 0:
        return None

    target_qty = max(0, order.target_qty or 0)
    if target_qty <= 0:
        return None

    good_qty = max(0, int(good_by_order.get(order.id, 0) or 0))
    remaining_qty = max(0, target_qty - good_qty)
    remaining_seconds = remaining_qty * article.cycle_time_s

    return {
        "at": now + timedelta(seconds=remaining_seconds),
        "remaining_qty": remaining_qty,
        "good_qty": good_qty,
        "target_qty": target_qty,
        "cycle_time_s": article.cycle_time_s,
        "duration_label": _format_duration(remaining_seconds),
    }


def _axis_ticks(range_start, range_end, step):
    ticks = []
    cursor = range_start.replace(minute=0, second=0, microsecond=0)
    if cursor < range_start:
        cursor += step

    while cursor <= range_end:
        ticks.append({
            "position": _percent(cursor, range_start, range_end),
            "time": cursor,
            "label": cursor.strftime("%H:%M"),
            "date_label": cursor.strftime("%d.%m."),
        })
        cursor += step
    return ticks


def get_machine_timeline(horizon_key="24h", now=None):
    now = now or datetime.utcnow()
    horizon_key = horizon_key if horizon_key in HORIZONS else "24h"
    horizon = HORIZONS[horizon_key]
    range_start = now - horizon["past"]
    range_end = now + horizon["future"]

    machines = (
        Machine.query
        .order_by(Machine.machine_no.asc(), Machine.name.asc())
        .all()
    )

    bookings = (
        TimeBooking.query
        .options(
            joinedload(TimeBooking.order),
            joinedload(TimeBooking.downtime_reason),
        )
        .filter(TimeBooking.machine_id.isnot(None))
        .filter(TimeBooking.start_time < range_end)
        .filter(or_(TimeBooking.end_time.is_(None), TimeBooking.end_time > range_start))
        .order_by(TimeBooking.machine_id.asc(), TimeBooking.start_time.asc())
        .all()
    )

    order_ids = {booking.order_id for booking in bookings if booking.order_id}
    good_by_order = {}
    if order_ids:
        quantity_rows = (
            db.session.query(
                QuantityReport.order_id,
                func.coalesce(func.sum(QuantityReport.good_qty), 0),
            )
            .filter(QuantityReport.order_id.in_(order_ids))
            .group_by(QuantityReport.order_id)
            .all()
        )
        good_by_order = {order_id: good_qty for order_id, good_qty in quantity_rows}

    article_numbers = {
        (booking.order.article or "").strip()
        for booking in bookings
        if booking.order and booking.order.article
    }
    articles_by_number = {}
    if article_numbers:
        articles = Article.query.filter(Article.article_no.in_(article_numbers)).all()
        articles_by_number = {article.article_no: article for article in articles}

    bookings_by_machine = {}
    for booking in bookings:
        bookings_by_machine.setdefault(booking.machine_id, []).append(booking)

    lanes = []
    counters = {
        "machines": len(machines),
        "production": 0,
        "setup": 0,
        "downtime": 0,
        "other": 0,
        "free": 0,
    }

    for machine in machines:
        machine_bookings = bookings_by_machine.get(machine.id, [])
        active_booking = next(
            (booking for booking in reversed(machine_bookings) if booking.end_time is None),
            None,
        )
        active_forecast = None
        items = []

        for booking in machine_bookings:
            process_label, color_class = PROCESS_META.get(
                booking.process,
                (booking.process or "Buchung", "other"),
            )
            visible_start = max(booking.start_time, range_start)
            actual_end = min(booking.end_time or now, range_end)

            if actual_end > visible_start:
                left = _percent(visible_start, range_start, range_end)
                right = _percent(actual_end, range_start, range_end)
                items.append({
                    "kind": "actual",
                    "class": color_class,
                    "left": left,
                    "width": max(0.35, right - left),
                    "label": _booking_label(booking, process_label),
                    "process_label": process_label,
                    "booking": booking,
                    "starts_before_range": booking.start_time < range_start,
                })

            if booking.end_time is None:
                forecast = _forecast_for(booking, good_by_order, articles_by_number, now)
                if forecast:
                    active_forecast = forecast
                    forecast_end = min(forecast["at"], range_end)
                    if forecast_end > now and now < range_end:
                        left = _percent(max(now, range_start), range_start, range_end)
                        right = _percent(forecast_end, range_start, range_end)
                        items.append({
                            "kind": "forecast",
                            "class": color_class,
                            "left": left,
                            "width": max(0.35, right - left),
                            "label": f"Prognose {booking.order.order_no}",
                            "process_label": "Fertigstellungsprognose",
                            "booking": booking,
                            "forecast": forecast,
                            "continues_after_range": forecast["at"] > range_end,
                        })

        if active_booking:
            _, active_class = PROCESS_META.get(
                active_booking.process,
                (active_booking.process or "Buchung", "other"),
            )
            if active_class == "production":
                counters["production"] += 1
            elif active_class == "setup":
                counters["setup"] += 1
            elif active_class == "downtime":
                counters["downtime"] += 1
            elif active_class == "free":
                counters["free"] += 1
            else:
                counters["other"] += 1
        else:
            counters["free"] += 1

        active_process_label = "Keine aktive Buchung"
        active_class = "free"
        if active_booking:
            active_process_label, active_class = PROCESS_META.get(
                active_booking.process,
                (active_booking.process or "Buchung", "other"),
            )

        lanes.append({
            "machine": machine,
            "items": items,
            "active_booking": active_booking,
            "active_forecast": active_forecast,
            "active_process_label": active_process_label,
            "active_class": active_class,
        })

    return {
        "lanes": lanes,
        "counters": counters,
        "horizon_key": horizon_key,
        "horizons": HORIZONS,
        "range_start": range_start,
        "range_end": range_end,
        "now": now,
        "now_position": _percent(now, range_start, range_end),
        "ticks": _axis_ticks(range_start, range_end, horizon["tick"]),
    }
