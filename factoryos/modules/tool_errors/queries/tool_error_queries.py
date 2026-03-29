from ..models import ToolError

from sqlalchemy.orm import joinedload

def get_tool_error(error_id):
    return ToolError.query\
        .options(
            joinedload(ToolError.images),
            joinedload(ToolError.tool)
        )\
        .get_or_404(error_id)
    
def get_tool_errors():

    return (
        ToolError.query
        .order_by(ToolError.created_at.desc())
        .all()
    )

