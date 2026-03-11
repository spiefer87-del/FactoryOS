class Gauge(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    gauge_no = db.Column(db.String(50), unique=True)

    name = db.Column(db.String(200))

    gauge_type = db.Column(db.String(50))

    manufacturer = db.Column(db.String(100))

    serial_no = db.Column(db.String(100))

    location = db.Column(db.String(100))

    status = db.Column(db.String(20), default="active")

    calibration_interval = db.Column(db.Integer)

    last_calibration = db.Column(db.Date)

    next_calibration = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class GaugeCalibration(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    gauge_id = db.Column(
        db.Integer,
        db.ForeignKey("gauge.id")
    )

    calibration_date = db.Column(db.Date)

    next_calibration = db.Column(db.Date)

    result = db.Column(db.String(20))

    certificate_no = db.Column(db.String(100))

    note = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )