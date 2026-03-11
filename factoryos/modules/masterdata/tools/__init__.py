from factoryos.modules.masterdata.core.registry import register_masterdata
from .models import ToolMasterdata


register_masterdata(
    name="tools",
    model=ToolMasterdata,
    search_fields=[
        "tool_no",
        "article_no",
        "article_name",
        "location",
        "tool_status"
    ]
)
