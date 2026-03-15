from factoryos.extensions import db
from factoryos.models.tools import ToolMasterdata


def create_tool(data):

    tool = ToolMasterdata(
        tool_no=data.get("tool_no"),
        article_no=data.get("article_no"),
        article_name=data.get("article_name"),
        location=data.get("location"),
        tool_status=data.get("tool_status")
    )

    db.session.add(tool)
    db.session.commit()

    return tool


def update_tool(tool, data):

    tool.tool_no = data.get("tool_no")
    tool.article_no = data.get("article_no")
    tool.article_name = data.get("article_name")
    tool.location = data.get("location")
    tool.tool_status = data.get("tool_status")

    db.session.commit()

    return tool