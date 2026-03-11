from datetime import datetime
from extensions import db

from factoryos.modules.quality.inspection_plan.models import QualityInspectionChangeLog


def log_change(version, action, message, user_id=None):
    """
    Schreibt einen Eintrag in das QM Änderungsprotokoll.
    """

    log = QualityInspectionChangeLog(

        plan_id=version.plan_id,
        version_id=version.id,

        action=action,
        message=message,

        user_id=user_id,

        created_at=datetime.utcnow()
    )

    db.session.add(log)