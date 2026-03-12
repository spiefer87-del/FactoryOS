from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from datetime import datetime
from dateutil.relativedelta import relativedelta

from factoryos.extensions import db
from factoryos.modules.quality.gauges.models import Gauge, GaugeCalibration
from factoryos.modules.quality.gauges.calibration_service import (
    calibration_status,
    create_gauge,
    create_gauge_calibration,
    update_gauge_status
)


gauges_bp = Blueprint(
    "gauges",
    __name__,
    url_prefix="/quality/gauges"
)


# -----------------------
# Gauge Übersicht
# -----------------------

@gauges_bp.route("/")
@login_required
def gauge_home():

    gauges = Gauge.query.order_by(Gauge.gauge_no).all()

    calibration_states = {}

    for g in gauges:
        calibration_states[g.id] = calibration_status(g)

    return render_template(
        "quality/gauges/gauge_home.html",
        gauges=gauges,
        calibration_states=calibration_states
    )


# -----------------------
# Neues Messmittel
# -----------------------

@gauges_bp.route("/new", methods=["GET","POST"])
@login_required
def gauge_new():

    if request.method == "POST":

        create_gauge(request.form)

        return redirect(url_for("gauges.gauge_home"))

    return render_template("quality/gauges/gauge_new.html")


# -----------------------
# Messmittel Detail
# -----------------------

@gauges_bp.route("/<int:gauge_id>")
@login_required
def gauge_detail(gauge_id):

    gauge = Gauge.query.get_or_404(gauge_id)

    calibrations = (
        GaugeCalibration.query
        .filter_by(gauge_id=gauge.id)
        .order_by(GaugeCalibration.calibration_date.desc())
        .all()
    )

    return render_template(
        "quality/gauges/gauge_detail.html",
        gauge=gauge,
        calibrations=calibrations
    )


# -----------------------
# Neue Kalibrierung
# -----------------------

@gauges_bp.route("/<int:gauge_id>/calibration/new", methods=["GET","POST"])
@login_required
def gauge_calibration_new(gauge_id):

    gauge = Gauge.query.get_or_404(gauge_id)

    if request.method == "POST":

        create_gauge_calibration(
            gauge_id,
            request.form
        )

        return redirect(
            url_for("gauges.gauge_detail", gauge_id=gauge.id)
        )

    return render_template(
        "quality/gauges/gauge_calibration_new.html",
        gauge=gauge
    )


# -----------------------
# Status ändern
# -----------------------

@gauges_bp.route("/<int:gauge_id>/status", methods=["POST"])
@login_required
def gauge_update_status(gauge_id):

    new_status = request.form.get("status")

    update_gauge_status(
        gauge_id,
        new_status
    )

    return redirect(
        url_for("gauges.gauge_detail", gauge_id=gauge_id)
    )
