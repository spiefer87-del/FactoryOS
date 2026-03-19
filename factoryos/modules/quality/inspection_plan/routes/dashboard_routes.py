from flask import render_template
from flask_login import login_required

from . import bp

@bp.route("/dashboard")
@login_required
def dashboard():

    plans = (
        QualityInspectionPlan.query
        .order_by(QualityInspectionPlan.id.desc())
        .all()
    )

    return render_template(
        "quality/inspection_plan/dashboard.html",
        plans=plans
    )
