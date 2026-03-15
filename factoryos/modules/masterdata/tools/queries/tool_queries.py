from factoryos.models.tools import ToolMasterdata


def get_tools(search, status, location):

    query = ToolMasterdata.query

    if search:
        query = query.filter(
            ToolMasterdata.tool_no.contains(search)
        )

    if status:
        query = query.filter(
            ToolMasterdata.tool_status == status
        )

    if location:
        query = query.filter(
            ToolMasterdata.location == location
        )

    tools = query.order_by(
        ToolMasterdata.tool_no
    ).all()

    statuses = ["aktiv", "wartung", "defekt"]

    locations = (
        ToolMasterdata.query
        .with_entities(ToolMasterdata.location)
        .distinct()
        .all()
    )

    locations = [l[0] for l in locations if l[0]]

    return tools, statuses, locations