from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from factoryos.extensions import db
from .order_statistics import order_statistics, forecast_data
from factoryos.models.machine import Machine
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import QuantityReport, TimeBooking
from factoryos.modules.production.services.calendar_service import (
    WEEKDAYS,
    calculate_production_finish,
    get_calendar_exceptions,
    get_non_working_periods,
    get_or_create_calendar_settings,
)


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
    "MUSTER": ("Musterung", "production"),
    "RUEST": ("Rüsten", "setup"),
    "ABRUEST": ("Abrüsten", "setup"),
    "STOERUNG": ("Störung", "downtime"),
    "PAUSE": ("Pause", "pause"),
    "FREI": ("Frei", "free"),
    "WARTUNG": ("Wartung", "other"),
    "SONSTIG": ("Sonstiger Vorgang", "other"),
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
        return ("Musterung " if booking.process == "MUSTER" else "") + booking.order.order_no
    if booking.process == "STOERUNG" and booking.downtime_reason:
        return booking.downtime_reason.name
    return process_label


def _forecast_for(
    booking,
    good_by_order,
    articles_by_number,
    now,
    calendar_settings,
    calendar_exceptions,
    tools_by_number=None,
):
    if booking.process not in ("PROD","MUSTER") or not booking.order:
        return None
    article=articles_by_number.get((booking.order.article or "").strip())
    number=(booking.tool_no or booking.order.tool_no or "").strip()
    tool=(tools_by_number or {}).get(number)
    source="Auftrags-/Buchungswerkzeug"
    if not number and article and len(article.tools)==1:
        tool=article.tools[0]
        source="Eindeutige Werkzeugzuordnung im Artikelstamm"
    result=forecast_data(booking.order, max(0,int(good_by_order.get(booking.order.id,0) or 0)),
                         article,tool,now,calendar_settings,calendar_exceptions)
    if result: result["tool_source"]=source if tool else "Kein eindeutiges Werkzeug"
    return result


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
    calendar_settings = get_or_create_calendar_settings()
    calendar_exceptions = get_calendar_exceptions()

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
        .filter(or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>TimeBooking.start_time))
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
        articles = Article.query.options(joinedload(Article.tools)).filter(Article.article_no.in_(article_numbers)).all()
        articles_by_number = {article.article_no: article for article in articles}

    bookings_by_machine = {}
    tool_numbers = {(booking.tool_no or booking.order.tool_no or "").strip()
                    for booking in bookings if booking.order}
    tools_by_number = {tool.tool_no: tool for tool in Tool.query.filter(Tool.tool_no.in_(tool_numbers)).all()} if tool_numbers else {}
    for booking in bookings:
        bookings_by_machine.setdefault(booking.machine_id, []).append(booking)

    stats_cache = {}
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
                forecast = None
                if booking.order and booking.process in ("PROD","MUSTER"):
                    if booking.order_id not in stats_cache:
                        stats_cache[booking.order_id] = order_statistics(booking.order,now,calendar_settings,calendar_exceptions)
                    stats = stats_cache[booking.order_id]
                    if stats["eta"] is not None and stats["active_booking"].id == booking.id:
                        forecast = stats["forecast"]
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

    weekday_names = dict(WEEKDAYS)
    calendar_closures = []
    for start_at, end_at, label in get_non_working_periods(
        range_start,
        range_end,
        calendar_settings,
        calendar_exceptions,
    ):
        left = _percent(start_at, range_start, range_end)
        right = _percent(end_at, range_start, range_end)
        calendar_closures.append({
            "start_at": start_at,
            "end_at": end_at,
            "label": label,
            "left": left,
            "width": max(0.15, right - left),
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
        "calendar_settings": calendar_settings,
        "calendar_closures": calendar_closures,
        "calendar_summary": (
            f"{weekday_names.get(calendar_settings.week_start_day)} "
            f"{calendar_settings.week_start_time} bis "
            f"{weekday_names.get(calendar_settings.week_end_day)} "
            f"{calendar_settings.week_end_time} Uhr"
        ),
    }
