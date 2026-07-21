from sqlalchemy import or_

from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article
from factoryos.core.models.change_log import ChangeLog


def get_tool(tool_id):

    return Tool.query.get_or_404(tool_id)


def get_tools(search, status, location):

    query = Tool.query

    if search:

        search_term = f"%{search}%"

        query = query.filter(
            or_(
                Tool.tool_no.ilike(search_term),
                Tool.external_tool_no.ilike(search_term),
                Tool.name.ilike(search_term),
                Tool.description.ilike(search_term),
                Tool.location.ilike(search_term),
                Tool.articles.any(
                    Article.article_no.ilike(search_term)
                ),
                Tool.articles.any(
                    Article.article_name.ilike(search_term)
                )
            )
        )

    if status:

        query = query.filter(
            Tool.tool_status == status
        )

    if location:

        query = query.filter(
            Tool.location == location
        )

    tools = (
        query
        .order_by(
            Tool.tool_no
        )
        .all()
    )

    statuses = [
        "aktiv",
        "wartung",
        "defekt",
        "external",
        "scrapped"
    ]

    locations = (
        Tool.query
        .with_entities(Tool.location)
        .distinct()
        .order_by(Tool.location)
        .all()
    )

    locations = [
        location[0]
        for location in locations
        if location[0]
    ]

    return tools, statuses, locations


def get_all_tools():

    return Tool.query.order_by(
        Tool.tool_no
    ).all()


def search_tools(search, limit=20):

    search_term = f"%{search}%"

    return (
        Tool.query
        .filter(
            or_(
                Tool.tool_no.ilike(search_term),
                Tool.external_tool_no.ilike(search_term),
                Tool.name.ilike(search_term)
            )
        )
        .order_by(
            Tool.tool_no
        )
        .limit(limit)
        .all()
    )
