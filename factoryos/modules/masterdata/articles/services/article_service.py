from factoryos.extensions import db
from ..models import Article
from factoryos.modules.masterdata.tools.models import Tool

from factoryos.core.services.change_log_service import log_change


# =========================
# 🔧 HELPER
# =========================

def to_float(value):
    if value in ("", None):
        return None
    return float(value)


def to_int(value):
    if value in ("", None):
        return None
    return int(value)


def build_changes(old_obj, new_data):
    changes = {}

    for field, new_value in new_data.items():
        old_value = getattr(old_obj, field)

        if str(old_value) != str(new_value):
            changes[field] = {
                "old": old_value,
                "new": new_value
            }

    return changes


# =========================
# 🆕 CREATE
# =========================

def create_article(form):

    tool_ids = form.getlist("tool_ids")

    article = Article(
        article_no=form.get("article_no"),
        article_name=form.get("article_name"),
        description=form.get("description"),
        status=form.get("status"),
        shot_weight_g=to_float(form.get("shot_weight_g")),
        cycle_time_s=to_float(form.get("cycle_time_s")),
        pack_unit=to_int(form.get("pack_unit")),
    )

    # 🔗 Tools verknüpfen
    if tool_ids:
        tools = Tool.query.filter(Tool.id.in_(tool_ids)).all()
        article.tools = tools

    db.session.add(article)
    db.session.flush()  # 🔥 wichtig für ID

    # 📝 ChangeLog
    log_change(
        entity_type="article",
        entity_id=article.id,
        entity_name=article.article_no,
        action="create",
        changes={
            "article_no": article.article_no,
            "article_name": article.article_name
        },
        category="masterdata"
    )

    # 🔗 Tool Verknüpfung loggen
    if tool_ids:
        log_change(
            entity_type="article",
            entity_id=article.id,
            action="link_tools",
            changes={
                "tools": tool_ids
            },
            category="masterdata"
        )

    db.session.commit()

    return article


# =========================
# ✏️ UPDATE
# =========================

def update_article(article, form):

    # neue Werte vorbereiten
    new_data = {
        "article_no": form.get("article_no"),
        "article_name": form.get("article_name"),
        "description": form.get("description"),
        "status": form.get("status"),
        "shot_weight_g": to_float(form.get("shot_weight_g")),
        "cycle_time_s": to_float(form.get("cycle_time_s")),
        "pack_unit": to_int(form.get("pack_unit")),
    }

    # 🔍 Feldänderungen erkennen
    changes = build_changes(article, new_data)

    # Werte setzen
    for key, value in new_data.items():
        setattr(article, key, value)

    # =========================
    # 🔗 TOOL VERKNÜPFUNG
    # =========================

    old_tools = set(article.tools)
    tool_ids = form.getlist("tools")

    new_tools = set(
        Tool.query.filter(Tool.id.in_(tool_ids)).all()
    ) if tool_ids else set()

    added_tools = new_tools - old_tools
    removed_tools = old_tools - new_tools

    article.tools = list(new_tools)

    # Tool Changes ergänzen
    if added_tools or removed_tools:
        changes["tools"] = {
            "added": [t.tool_no for t in added_tools],
            "removed": [t.tool_no for t in removed_tools]
        }

    # =========================
    # 📝 CHANGELOG
    # =========================

    if changes:
        log_change(
            entity_type="article",
            entity_id=article.id,
            action="update",
            changes=changes,
            category="masterdata"
        )

    db.session.commit()

    return article


# =========================
# 🗑 DELETE
# =========================

def delete_article(article):

    log_change(
        entity_type="article",
        entity_id=article.id,
        action="delete",
        changes={
            "article_no": article.article_no,
            "article_name": article.article_name
        },
        category="masterdata"
    )

    db.session.delete(article)
    db.session.commit()
