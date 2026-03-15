from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user

from factoryos.core.auth import role_required
from factoryos.modules.reports.services import (
    get_time_report,
    export_time_report_excel,
    get_order_report
)

bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/reports"
)


@bp.route("/times")
@login_required
def report_times():

    data = get_time_report(request.args)

    return render_template(
        "reports/times.html",
        **data
    )


@bp.route("/times/export")
@login_required
@role_required("admin", "schichtleiter")
def report_times_export():

    file_data = export_time_report_excel(request.args)

    return send_file(
        file_data,
        as_attachment=True,
        download_name="zeitauswertung.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@bp.route("/orders")
@login_required
@role_required("admin", "schichtleiter")
def report_orders():

    report = get_order_report()

    return render_template(
        "reports/orders.html",
        report=report
    )