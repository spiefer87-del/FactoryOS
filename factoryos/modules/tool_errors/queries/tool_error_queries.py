from sqlalchemy import or_

from ..models import ToolError


def get_tool_errors(include_history=False):

    query = ToolError.query

    # Standard:
    # Nur aktuelle Revisionen anzeigen.
    #
    # is_current IS NULL ist als Fallback für alte Datensätze gedacht,
    # die vor Einführung der Revisionierung erstellt wurden.
    if not include_history:

        query = query.filter(
            or_(
                ToolError.is_current.is_(True),
                ToolError.is_current.is_(None)
            )
        )

    return (
        query
        .order_by(
            ToolError.created_at.desc(),
            ToolError.id.desc()
        )
        .all()
    )


def get_tool_error(error_id):

    return ToolError.query.get_or_404(error_id)
