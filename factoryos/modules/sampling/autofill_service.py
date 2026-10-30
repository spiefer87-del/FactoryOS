"""Suggestions only: never turn master-data targets into measured results."""
from sqlalchemy.orm import joinedload
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.tools.models import Tool


def article_defaults(article):
    tools = sorted(article.tools, key=lambda t: (t.tool_no or "", t.id))
    return {
        "customer_id": str(article.customer_id or ""),
        "material_id": str(article.material_id or ""),
        "tool_id": str(tools[0].id) if len(tools) == 1 else "",
        "tool_count": len(tools),
        "tool_names": [t.tool_no for t in tools],
        "color": article.masterbatch.color if article.masterbatch else "",
        "masterbatch_id": str(article.masterbatch_id or ""),
        "masterbatch": " / ".join([article.masterbatch.material_no, article.masterbatch.name]) if article.masterbatch else "",
        "masterbatch_percent": article.masterbatch_percent,
        "ral_color": article.masterbatch.ral_color if article.masterbatch else "",
        "reference": {
            "Artikel": article.article_no,
            "Farbe laut Artikel": article.masterbatch.color if article.masterbatch else "-",
            "Farbbatch laut Artikel": article.masterbatch.material_no if article.masterbatch else "-",
            "Farbbatch-Zugabe laut Artikel (% vom Hauptrohstoffgewicht)": article.masterbatch_percent,
            "Gewünschter Farbton / RAL laut Artikel": article.masterbatch.ral_color if article.masterbatch else "-",
            "Zeichnungsnummer": article.drawing_no or "-",
            "Zeichnungsindex": article.drawing_revision or "-",
            "Zykluszeit laut Artikel (s)": article.cycle_time_s,
            "Schussgewicht laut Artikel (g)": article.shot_weight_g,
            "Verpackungseinheit laut Artikel": article.pack_unit,
        },
    }


def autofill_catalog():
    articles = Article.query.options(joinedload(Article.tools), joinedload(Article.masterbatch)).all()
    return {
        "articles": {str(a.id): article_defaults(a) for a in articles},
        "materials": {str(m.id): {
            "color": m.color or "",
            "ral_color": m.ral_color or "",
            "material_type": m.material_type,
            "label": " / ".join([m.material_no, m.name]),
            "reference": {"Materialnummer": m.material_no, "Material": m.name,
                          "Kunststoffart": m.polymer_type or "-",
                          "Trocknungstemperatur laut Material (°C)": m.drying_temperature_c,
                          "Trocknungszeit laut Material (h)": m.drying_time_h},
        } for m in Material.query.all()},
        "tools": {str(t.id): {
            "reference": {"Werkzeugnummer": t.tool_no, "Werkzeuglagerort": t.location or "-",
                          "Kavitäten laut Werkzeug": t.cavities},
        } for t in Tool.query.all()},
    }


def reference_snapshot(article, tool, material):
    result = {}
    if article:
        result.update(article_defaults(article)["reference"])
    if tool:
        result.update({"Werkzeugnummer": tool.tool_no, "Werkzeuglagerort": tool.location or "-",
                       "Kavitäten laut Werkzeug": tool.cavities})
    if material:
        result.update({"Materialnummer": material.material_no, "Material": material.name,
                       "Kunststoffart": material.polymer_type or "-",
                       "Trocknungstemperatur laut Material (°C)": material.drying_temperature_c,
                       "Trocknungszeit laut Material (h)": material.drying_time_h})
    return result


def material_confirmed(record):
    confirmation = (record.data or {}).get("material_confirmation") or {}
    return (record.material_id is not None and
            confirmation.get("material_id") == record.material_id and
            confirmation.get("article_id") == record.article_id)


COLOR_KEYS = ("color", "masterbatch", "masterbatch_id", "masterbatch_percent", "ral_color")


def color_signature(data, article_id, material_id):
    return {"article_id": article_id, "material_id": material_id,
            **{key: data.get(key) for key in COLOR_KEYS}}


def color_confirmed(record):
    data = record.data or {}
    confirmation = data.get("color_confirmation") or {}
    return (bool(data.get("color") or data.get("ral_color")) and
            confirmation.get("values") == color_signature(data, record.article_id, record.material_id))

