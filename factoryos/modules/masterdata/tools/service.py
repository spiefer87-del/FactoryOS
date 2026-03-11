from factoryos.models.tools import ToolMasterdata
from extensions import db
from factoryos.modules.masterdata.core.search_service import search_query
from factoryos.modules.masterdata.core.crud_service import (
    create_row,
    update_row,
    delete_row
)


def search_tools(q):

    query = ToolMasterdata.query

    query = search_query(
        query,
        ToolMasterdata,
        [
            "tool_no",
            "article_no",
            "article_name",
            "location",
            "tool_status"
        ],
        q
    )

    return query.order_by(ToolMasterdata.tool_no.asc()).all()


def create_tool(data):

    payload = {
        "tool_no": data.get("tool_no"),
        "article_no": data.get("article_no"),
        "article_name": data.get("article_name"),
        "location": data.get("location"),
    }

    return create_row(ToolMasterdata, payload)


def update_tool(row, data):

    payload = {
        "tool_no": data.get("tool_no"),
        "article_no": data.get("article_no"),
        "article_name": data.get("article_name"),
        "location": data.get("location"),
    }

    return update_row(row, payload)


def delete_tool(tool_id):

    row = ToolMasterdata.query.get_or_404(tool_id)

    return delete_row(row)