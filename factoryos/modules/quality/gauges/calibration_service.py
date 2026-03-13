from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from factoryos.extensions import db
from factoryos.modules.quality.gauges.models import Gauge, GaugeCalibration


# --------------------------------------------------
# Kalibrierstatus berechnen
# --------------------------------------------------

def calibration_status(gauge):

    if not gauge.next_calibration:
        return "unknown"

    today = date.today()

    if gauge.next_calibration < today:
        return "overdue"

    days_left = (gauge.next_calibration - today).days

    if days_left <= 30:
        return "warning"

    return "ok"


# --------------------------------------------------
# Nächste Kalibrierung berechnen
# --------------------------------------------------

def calculate_next_calibration(calibration_date, interval):

    try:
        interval = int(interval)
    except (TypeError, ValueError):
        return None

    if not calibration_date:
        return None

    return calibration_date + relativedelta(months=interval)


# --------------------------------------------------
# Neues Messmittel erstellen
# --------------------------------------------------

def create_gauge(data):

    last_calibration = data.get("last_calibration")
    interval = data.get("calibration_interval")

    if last_calibration:
        last_calibration = datetime.strptime(
            last_calibration,
            "%Y-%m-%d"
        ).date()

    try:
        interval = int(interval) if interval else None
    except ValueError:
        interval = None

    next_calibration = calculate_next_calibration(
        last_calibration,
        interval
    )

    gauge = Gauge(
        gauge_no=data.get("gauge_no"),
        name=data.get("name"),
        gauge_type=data.get("gauge_type"),
        manufacturer=data.get("manufacturer"),
        serial_no=data.get("serial_no"),
        location=data.get("location"),
        calibration_interval=interval,
        last_calibration=last_calibration,
        next_calibration=next_calibration,
        status="active"
    )

    db.session.add(gauge)
    db.session.commit()

    return gauge


# --------------------------------------------------
# Kalibrierung erstellen
# --------------------------------------------------

def create_gauge_calibration(gauge_id, data):

    gauge = Gauge.query.get(gauge_id)

    if not gauge:
        raise ValueError("Gauge not found")

    calibration_date = data.get("calibration_date")

    if not calibration_date:
        raise ValueError("Calibration date required")

    calibration_date = datetime.strptime(
        calibration_date,
        "%Y-%m-%d"
    ).date()

    next_calibration = calculate_next_calibration(
        calibration_date,
        gauge.calibration_interval
    )

    calibration = GaugeCalibration(
        gauge_id=gauge.id,
        calibration_date=calibration_date,
        next_calibration=next_calibration,
        result=data.get("result"),
        certificate_no=data.get("certificate_no"),
        note=data.get("note")
    )

    db.session.add(calibration)

    gauge.last_calibration = calibration_date
    gauge.next_calibration = next_calibration

    db.session.commit()

    return calibration


# --------------------------------------------------
# Messmittelstatus ändern
# --------------------------------------------------

def update_gauge_status(gauge_id, new_status):

    allowed = ["active", "inspection", "inactive"]

    if new_status not in allowed:
        raise ValueError("Invalid status")

    gauge = Gauge.query.get(gauge_id)

    if not gauge:
        raise ValueError("Gauge not found")

    gauge.status = new_status

    db.session.commit()

    return gauge
