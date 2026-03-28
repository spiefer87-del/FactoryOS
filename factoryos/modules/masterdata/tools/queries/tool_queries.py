from factoryos.modules.masterdata.tools.models import Tool
from factoryos.core.models.change_log import ChangeLog

def get_tool(tool_id):
    return Tool.query.get_or_404(tool_id)

def get_tools(search, status, location):

    query = Tool.query

    if search:
        query = query.filter(
            Tool.tool_no.contains(search)
        )

    if status:
        query = query.filter(
            Tool.tool_status == status
        )

    if location:
        query = query.filter(
            Tool.location == location
        )

    tools = query.order_by(
        Tool.tool_no
    ).all()

    statuses = ["aktiv", "wartung", "defekt"]

    locations = (
        Tool.query
        .with_entities(Tool.location)
        .distinct()
        .all()
    )

    locations = [l[0] for l in locations if l[0]]

    return tools, statuses, locations


