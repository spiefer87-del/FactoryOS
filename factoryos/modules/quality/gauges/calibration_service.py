from datetime import datetime
from dateutil.relativedelta import relativedelta

from factoryos.extensions import db
from factoryos.modules.quality.models import Gauge, GaugeCalibration


# --------------------------------------------------
# Kalibrierstatus berechnen
# --------------------------------------------------

def calibration_status(gauge):

    if not gauge.next_calibration:
        return "unknown"

    today = datetime.utcnow().date()

    if gauge.next_calibration < today:
        return "overdue"

    if (gauge.next_calibration - today).days <= 30:
        return "warning"

    return "ok"


# --------------------------------------------------
# Nächste Kalibrierung berechnen
# --------------------------------------------------

def calculate_next_calibration(calibration_date, interval):

    if not calibration_date or not interval:
        return None

    return calibration_date + relativedelta(months=int(interval))


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
        next_calibration=next_calibration
    )

    db.session.add(gauge)
    db.session.commit()

    return gauge


# --------------------------------------------------
# Kalibrierung erstellen
# --------------------------------------------------

def create_gauge_calibration(gauge_id, data):

    gauge = Gauge.query.get_or_404(gauge_id)

    calibration_date = data.get("calibration_date")

    if calibration_date:
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
        return None

    gauge = Gauge.query.get_or_404(gauge_id)

    gauge.status = new_status

    db.session.commit()


    return gauge
