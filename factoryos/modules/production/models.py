class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    tool_no = db.Column(db.String(50), nullable=True)
    is_project = db.Column(db.Boolean, default=False)
    article = db.Column(db.String(120), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    project_leader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    project_leader = db.relationship("User", foreign_keys=[project_leader_id])
    article_name = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(100), nullable=True)


    target_qty = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="offen")  # offen, in_arbeit, fertig, gesperrt


class DowntimeReason(db.Model):
    __tablename__ = "downtime_reasons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class TimeBooking(db.Model):
    __tablename__ = "time_bookings"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=True)
    process = db.Column(db.String(20), default="PROD")  # PROD, RUEST, ABRUEST
    tool_no = db.Column(db.String(50), nullable=True)


    # START, PAUSE, STOP, STOERUNG
    type = db.Column(db.String(20), nullable=False)

    start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)  # NULL = aktiv
    prev_order_id = db.Column(db.Integer, nullable=True)

    comment = db.Column(db.String(255), nullable=True)

    downtime_reason_id = db.Column(db.Integer, db.ForeignKey("downtime_reasons.id"), nullable=True)

    user = db.relationship("User", backref="bookings")
    order = db.relationship("Order", backref="bookings")
    machine = db.relationship("Machine", backref="bookings")
    downtime_reason = db.relationship("DowntimeReason", backref="bookings")

    @property
    def is_active(self):
        return self.end_time is None

class QuantityReport(db.Model):
    __tablename__ = "quantity_reports"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)

    good_qty = db.Column(db.Integer, default=0)
    scrap_qty = db.Column(db.Integer, default=0)

    note = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref="qty_reports")
    order = db.relationship("Order", backref="qty_reports")
    machine = db.relationship("Machine", backref="qty_reports")
