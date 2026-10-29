from datetime import date, datetime, time, timedelta

from factoryos.extensions import db
from factoryos.modules.production.models import (
    ProductionCalendarException,
    ProductionCalendarSettings,
)


WEEKDAYS = (
    (0, "Montag"),
    (1, "Dienstag"),
    (2, "Mittwoch"),
    (3, "Donnerstag"),
    (4, "Freitag"),
    (5, "Samstag"),
    (6, "Sonntag"),
)

DEFAULT_START_DAY = 0
DEFAULT_START_TIME = "04:30"
DEFAULT_END_DAY = 5
DEFAULT_END_TIME = "06:00"


def get_or_create_calendar_settings(commit=True):
    settings = ProductionCalendarSettings.query.order_by(
        ProductionCalendarSettings.id.asc()
    ).first()
    if settings is None:
        settings = ProductionCalendarSettings(
            week_start_day=DEFAULT_START_DAY,
            week_start_time=DEFAULT_START_TIME,
            week_end_day=DEFAULT_END_DAY,
            week_end_time=DEFAULT_END_TIME,
        )
        db.session.add(settings)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
    return settings


def parse_clock(value):
    try:
        parsed = datetime.strptime((value or "").strip(), "%H:%M")
    except ValueError as exc:
        raise ValueError("Bitte eine gültige Uhrzeit eingeben.") from exc
    return parsed.time().replace(second=0, microsecond=0)


def parse_weekday(value):
    try:
        weekday = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Bitte einen gültigen Wochentag auswählen.") from exc
    if weekday not in range(7):
        raise ValueError("Bitte einen gültigen Wochentag auswählen.")
    return weekday


def validate_weekly_window(start_day, start_time, end_day, end_time):
    start_day = parse_weekday(start_day)
    end_day = parse_weekday(end_day)
    start_clock = parse_clock(start_time)
    end_clock = parse_clock(end_time)

    start_offset = _weekly_offset(start_day, start_clock)
    end_offset = _weekly_offset(end_day, end_clock)
    if end_offset <= start_offset:
        end_offset += timedelta(days=7)

    duration = end_offset - start_offset
    if duration <= timedelta(0) or duration >= timedelta(days=7):
        raise ValueError("Das Produktionsfenster muss kürzer als sieben Tage sein.")

    return start_day, start_clock, end_day, end_clock


def update_calendar_settings(settings, form):
    start_day, start_clock, end_day, end_clock = validate_weekly_window(
        form.get("week_start_day"),
        form.get("week_start_time"),
        form.get("week_end_day"),
        form.get("week_end_time"),
    )
    settings.week_start_day = start_day
    settings.week_start_time = start_clock.strftime("%H:%M")
    settings.week_end_day = end_day
    settings.week_end_time = end_clock.strftime("%H:%M")
    db.session.commit()
    return settings


def create_calendar_exception(form, user_id=None):
    title = (form.get("title") or "").strip()
    if not title:
        raise ValueError("Bitte eine Bezeichnung für die Ausnahme eingeben.")

    try:
        start_date = date.fromisoformat(form.get("start_date") or "")
        end_date = date.fromisoformat(form.get("end_date") or form.get("start_date") or "")
    except ValueError as exc:
        raise ValueError("Bitte ein gültiges Start- und Enddatum eingeben.") from exc

    if end_date < start_date:
        raise ValueError("Das Enddatum darf nicht vor dem Startdatum liegen.")

    all_day = form.get("all_day") == "yes"
    if all_day:
        start_at = datetime.combine(start_date, time.min)
        end_at = datetime.combine(end_date + timedelta(days=1), time.min)
    else:
        start_clock = parse_clock(form.get("start_time"))
        end_clock = parse_clock(form.get("end_time"))
        start_at = datetime.combine(start_date, start_clock)
        end_at = datetime.combine(end_date, end_clock)
        if end_at <= start_at:
            raise ValueError("Das Ende der Ausnahme muss nach dem Beginn liegen.")

    exception = ProductionCalendarException(
        title=title[:160],
        start_at=start_at,
        end_at=end_at,
        all_day=all_day,
        note=(form.get("note") or "").strip()[:500] or None,
        created_by_id=user_id,
    )
    db.session.add(exception)
    db.session.commit()
    return exception


def delete_calendar_exception(exception_id):
    exception = db.session.get(ProductionCalendarException, exception_id)
    if exception is None:
        return False
    db.session.delete(exception)
    db.session.commit()
    return True


def get_calendar_exceptions():
    return ProductionCalendarException.query.order_by(
        ProductionCalendarException.start_at.asc(),
        ProductionCalendarException.id.asc(),
    ).all()


def calculate_production_finish(start_at, production_seconds, settings, exceptions):
    """Add working seconds while skipping the weekly shutdown and exceptions."""

    remaining = max(0.0, float(production_seconds or 0))
    if remaining == 0:
        return start_at

    exceptions = sorted(
        (item for item in exceptions if item.end_at > start_at),
        key=lambda item: (item.start_at, item.end_at),
    )
    cursor = start_at

    for _ in range(100000):
        window_start, window_end = _production_window_at_or_after(cursor, settings)
        cursor = max(cursor, window_start)

        blocking = next(
            (
                item
                for item in exceptions
                if item.end_at > cursor and item.start_at < window_end
            ),
            None,
        )

        if blocking and blocking.start_at <= cursor:
            cursor = max(cursor, blocking.end_at)
            continue

        available_end = min(window_end, blocking.start_at) if blocking else window_end
        available_seconds = max(0.0, (available_end - cursor).total_seconds())

        if remaining <= available_seconds:
            return cursor + timedelta(seconds=remaining)

        remaining -= available_seconds
        cursor = blocking.end_at if blocking else window_end

    raise RuntimeError("Produktionsende konnte nicht innerhalb des Sicherheitslimits berechnet werden.")


def get_non_working_periods(range_start, range_end, settings, exceptions):
    """Return merged shutdown periods for display in the timeline."""

    if range_end <= range_start:
        return []

    working = []
    cursor = range_start
    for _ in range(2000):
        start_at, end_at = _production_window_at_or_after(cursor, settings)
        if start_at >= range_end:
            break
        working.append((max(start_at, range_start), min(end_at, range_end)))
        cursor = end_at + timedelta(microseconds=1)

    closures = _complement(range_start, range_end, working)
    for item in exceptions:
        if item.end_at <= range_start or item.start_at >= range_end:
            continue
        closures.append((
            max(item.start_at, range_start),
            min(item.end_at, range_end),
            item.title,
        ))

    return _merge_closures(closures)


def _weekly_offset(weekday, clock):
    return timedelta(
        days=weekday,
        hours=clock.hour,
        minutes=clock.minute,
    )


def _settings_offsets(settings):
    start_clock = parse_clock(settings.week_start_time)
    end_clock = parse_clock(settings.week_end_time)
    start_offset = _weekly_offset(settings.week_start_day, start_clock)
    end_offset = _weekly_offset(settings.week_end_day, end_clock)
    if end_offset <= start_offset:
        end_offset += timedelta(days=7)
    return start_offset, end_offset


def _monday(value):
    return datetime.combine(value.date() - timedelta(days=value.weekday()), time.min)


def _production_window_at_or_after(value, settings):
    start_offset, end_offset = _settings_offsets(settings)
    monday = _monday(value)

    candidates = []
    for week_delta in (-1, 0, 1, 2):
        anchor = monday + timedelta(days=7 * week_delta)
        start_at = anchor + start_offset
        end_at = anchor + end_offset
        if end_at > value:
            candidates.append((start_at, end_at))

    if not candidates:
        anchor = monday + timedelta(days=14)
        return anchor + start_offset, anchor + end_offset

    containing = [window for window in candidates if window[0] <= value < window[1]]
    if containing:
        return min(containing, key=lambda window: window[0])
    return min((window for window in candidates if window[0] >= value), key=lambda window: window[0])


def _complement(range_start, range_end, intervals):
    closures = []
    cursor = range_start
    for start_at, end_at in sorted(intervals):
        if start_at > cursor:
            closures.append((cursor, start_at, "Keine Produktionszeit"))
        cursor = max(cursor, end_at)
    if cursor < range_end:
        closures.append((cursor, range_end, "Keine Produktionszeit"))
    return closures


def _merge_closures(closures):
    merged = []
    for start_at, end_at, label in sorted(closures, key=lambda item: item[0]):
        if end_at <= start_at:
            continue
        if merged and start_at <= merged[-1][1]:
            previous_start, previous_end, previous_labels = merged[-1]
            labels = previous_labels
            if label not in labels:
                labels = f"{labels}, {label}"
            merged[-1] = (previous_start, max(previous_end, end_at), labels)
        else:
            merged.append((start_at, end_at, label))
    return merged
