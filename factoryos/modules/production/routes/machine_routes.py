"""Legacy entry points lead to the authoritative touch panel.
Old POST bodies never change a state without revision, UUID and CSRF.
"""
from flask import redirect, url_for
from flask_login import login_required
from . import bp

@bp.route("/machine/<int:machine_id>/setup",methods=["GET","POST"])
@login_required
def machine_setup(machine_id):
    return redirect(url_for("production.machine_control",machine_id=machine_id),code=303)

@bp.route("/machine/<int:machine_id>/event",methods=["GET","POST"])
@login_required
def machine_event(machine_id):
    return redirect(url_for("production.machine_control",machine_id=machine_id),code=303)

@bp.route("/machine/<int:machine_id>/downtime",methods=["GET","POST"])
@login_required
def machine_downtime(machine_id):
    return redirect(url_for("production.machine_control",machine_id=machine_id),code=303)
