from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool


def create_tool(data):

    tool = Tool(
        tool_no=data.get("tool_no"),
        name=data.get("name"),
        description=data.get("description"),
        location=data.get("location"),
        tool_status=data.get("tool_status"),
        cavities=data.get("cavities") or None,
    )

    db.session.add(tool)
    db.session.commit()

    return tool


def update_tool(tool, data):

    tool.tool_no = data.get("tool_no")
    tool.name = data.get("name")
    tool.description = data.get("description")
    tool.location = data.get("location")
    tool.tool_status = data.get("tool_status")
    tool.cavities = data.get("cavities") or None


    db.session.commit()

    return tool