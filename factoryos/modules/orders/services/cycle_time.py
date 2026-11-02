"""Common target-cycle validation. Seconds per machine cycle, never a measured value."""
import math


def parse_cycle_time(value):
    try:
        number = float(str(value).strip().replace(",", "."))
        if not math.isfinite(number) or number <= 0:
            raise ValueError()
    except (ValueError, TypeError, OverflowError):
        raise ValueError("Soll-Zykluszeit ist Pflicht und muss eine endliche Zahl größer als 0 Sekunden sein.")
    return number


def valid_cycle_time(value):
    try:
        return parse_cycle_time(value)
    except ValueError:
        return None
