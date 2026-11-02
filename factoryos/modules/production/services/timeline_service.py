from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from .order_statistics import order_statistics, forecast_data, local_time
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.calendar_service import (
    WEEKDAYS,
    get_calendar_exceptions,
    get_non_working_periods,
    get_or_create_calendar_settings,
)


HORIZONS = {
    "1h": {"label":"1 Stunde","past":timedelta(minutes=15),"future":timedelta(minutes=45),"tick":timedelta(minutes=10)},
    "8h": {"label":"8 Stunden","past":timedelta(hours=2),"future":timedelta(hours=6),"tick":timedelta(hours=1)},
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
    "30d": {"label":"30 Tage","past":timedelta(days=7),"future":timedelta(days=23),"tick":timedelta(days=2)},
}

MAX_CUSTOM_SPAN=timedelta(days=366)

def parse_timeline_range(start,end,start_fold="",end_fold=""):
    from .booking_time_service import parse_local_start
    try:
        first=parse_local_start(start,start_fold)
        last=parse_local_start(end,end_fold)
    except ValueError as exc:
        raise ValueError("Zeitraum: "+str(exc)) from exc
    validate_timeline_range(first,last)
    return first,last

def validate_timeline_range(start,end):
    if not isinstance(start,datetime) or not isinstance(end,datetime) or start.tzinfo or end.tzinfo:
        raise ValueError("Bitte Beginn und Ende des Zeitraums angeben.")
    if start<datetime(1970,1,1) or end>=datetime(2101,1,1):
        raise ValueError("Bitte einen Zeitraum zwischen 1970 und 2100 wählen.")
    if end-start<timedelta(minutes=1):
        raise ValueError("Das Ende muss mindestens eine Minute nach dem Beginn liegen.")
    if end-start>MAX_CUSTOM_SPAN:
        raise ValueError("Bitte höchstens 366 Tage auf einmal anzeigen.")

def _custom_tick(span):
    for minutes in (1,5,10,30,60,120,360,720,1440,2880,10080,20160,43200):
        if timedelta(minutes=minutes)>=span/16:return timedelta(minutes=minutes)
    return timedelta(days=30)

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
    origin=datetime(1970,1,1)
    cursor=origin+((range_start-origin)//step)*step
    if cursor < range_start:
        cursor += step

    while cursor <= range_end:
        ticks.append({
            "position": _percent(cursor, range_start, range_end),
            "time": cursor,
            "label": local_time(cursor).strftime("%H:%M %Z"),
            "date_label": local_time(cursor).strftime("%d.%m."),
        })
        cursor += step
    return ticks


def get_machine_timeline(horizon_key="24h", now=None, range_start=None, range_end=None):
    now = now or datetime.utcnow()
    if horizon_key=="custom":
        validate_timeline_range(range_start,range_end)
        tick_step=_custom_tick(range_end-range_start)
    else:
        horizon_key = horizon_key if horizon_key in HORIZONS else "24h"
        horizon = HORIZONS[horizon_key]
        range_start = now - horizon["past"]
        range_end = now + horizon["future"]
        tick_step=horizon["tick"]
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
    # Current status/controls must not depend on the historical display window.
    active_bookings=(TimeBooking.query.options(joinedload(TimeBooking.order),joinedload(TimeBooking.downtime_reason))
        .filter(TimeBooking.machine_id.isnot(None),TimeBooking.end_time.is_(None))
        .order_by(TimeBooking.start_time,TimeBooking.id).all())
    active_by_machine={}
    for booking in active_bookings:active_by_machine.setdefault(booking.machine_id,[]).append(booking)
    bookings=sorted({b.id:b for b in [*bookings,*active_bookings]}.values(),key=lambda b:(b.machine_id,b.start_time,b.id))

    bookings_by_machine = {}
    for booking in bookings:
        bookings_by_machine.setdefault(booking.machine_id, []).append(booking)

    stats_cache = {}
    from .planning_service import build_schedule
    schedule=build_schedule(now,calendar_settings,calendar_exceptions)
    planned_by_machine={lane["machine"].id:lane for lane in schedule["machines"]}
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
        current=active_by_machine.get(machine.id,[])
        active_booking=current[-1] if current else None
        active_forecast = None
        items = []

        for booking in machine_bookings:
            process_label, color_class = PROCESS_META.get(
                booking.process,
                (booking.process or "Buchung", "other"),
            )
            visible_start = max(booking.start_time, range_start)
            actual_end = min(booking.end_time or now, now, range_end)

            if actual_end > visible_start:
                left = _percent(visible_start, range_start, range_end)
                right = _percent(actual_end, range_start, range_end)
                items.append({
                    "kind": "actual",
                    "class": color_class,
                    "left": left,
                    "width": min(100-left,max(0.35, right - left)),
                    "label": _booking_label(booking, process_label),
                    "process_label": process_label,
                    "booking": booking,
                    "starts_before_range": booking.start_time < range_start,
                })

            if booking.end_time is None:
                forecast = None
                if len(current)==1 and booking.start_time<=now and booking.order and booking.process in ("PROD","MUSTER"):
                    if booking.order_id not in stats_cache:
                        stats_cache[booking.order_id] = order_statistics(booking.order,now,calendar_settings,calendar_exceptions)
                    stats = stats_cache[booking.order_id]
                    if stats["eta"] is not None and stats["active_booking"].id == booking.id:
                        forecast = stats["forecast"]
                if forecast:
                    active_forecast = forecast
                    forecast_end = min(forecast["at"], range_end)
                    if forecast_end > max(now,range_start) and now < range_end:
                        left = _percent(max(now, range_start), range_start, range_end)
                        right = _percent(forecast_end, range_start, range_end)
                        items.append({
                            "kind": "forecast",
                            "class": color_class,
                            "left": left,
                            "width": min(100-left,max(0.35, right - left)),
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

        plan_lane=planned_by_machine.get(machine.id,{"rows":[],"warnings":[],"error":None})
        for row in plan_lane["rows"]:
            if not row["start"]:continue
            for phase,start,end in (("setup",row["setup_start"],row["setup_end"]),("production",row["start"],row["end"])):
                start=max(start,range_start);end=min(end,range_end)
                if end<=start:continue
                segments=[(start,end)]
                for closure_start,closure_end,_ in get_non_working_periods(start,end,calendar_settings,calendar_exceptions):
                    updated=[]
                    for left_edge,right_edge in segments:
                        if closure_end<=left_edge or closure_start>=right_edge:updated.append((left_edge,right_edge));continue
                        if left_edge<closure_start:updated.append((left_edge,closure_start))
                        if closure_end<right_edge:updated.append((closure_end,right_edge))
                    segments=updated
                for left_edge,right_edge in segments:
                    left=_percent(left_edge,range_start,range_end);right=_percent(right_edge,range_start,range_end)
                    items.append(dict(kind="planned",phase=phase,**{"class":"planned-"+phase},
                        left=left,width=min(100-left,max(0.2,right-left)),row=row,
                        label=f"Plan {row['entry'].position}: {row['entry'].order.order_no}"+(" · Rüsten" if phase=="setup" else "")))

        lanes.append({
            "machine": machine,
            "items": items,
            "active_booking": active_booking,
            "active_forecast": active_forecast,
            "active_process_label": active_process_label,
            "active_class": active_class,
            "active_count": len(current),
            "plan_rows": plan_lane["rows"],
            "plan_error": plan_lane["error"],
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
            "width": min(100-left,max(0.15, right - left)),
        })

    ticks=_axis_ticks(range_start,range_end,tick_step)
    return {
        "lanes": lanes,
        "counters": counters,
        "horizon_key": horizon_key,
        "horizons": HORIZONS,
        "range_start": range_start,
        "range_end": range_end,
        "now": now,
        "now_position": _percent(now, range_start, range_end),
        "show_now": range_start<=now<=range_end,
        "ticks": ticks,
        "track_width": max(840,len(ticks)*95),
        "planning_version": schedule["version"],
        "planning_blocked": sum(1 for lane in schedule["machines"] for row in lane["rows"] if row["error"]),
        "calendar_settings": calendar_settings,
        "calendar_closures": calendar_closures,
        "calendar_summary": (
            f"{weekday_names.get(calendar_settings.week_start_day)} "
            f"{calendar_settings.week_start_time} bis "
            f"{weekday_names.get(calendar_settings.week_end_day)} "
            f"{calendar_settings.week_end_time} Uhr"
        ),
    }
