from ..models import ToolError


def get_tool_errors():

    return (
        ToolError.query
        .order_by(ToolError.created_at.desc())
        .all()
    )


def get_tool_error(error_id):

    return ToolError.query.get_or_404(error_id)
