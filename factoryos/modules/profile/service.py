from factoryos.extensions import db
from .models import UserPreference

ARTICLE_COLUMNS = ("article_no", "article_name", "customer", "material", "tools", "status", "sampling", "actions")
TOOL_COLUMNS = ("tool_no", "external_tool_no", "name", "article_no", "article_name", "location", "status", "built_by", "build_year", "shot_counter", "cavities", "core_pulls", "hotrunner_zones", "weight", "dimensions", "description", "actions")
TOOL_DEFAULTS = {key: key in ("tool_no", "external_tool_no", "name", "article_no", "article_name", "location", "status", "actions") for key in TOOL_COLUMNS}
DEFAULTS = {"articles.columns": {key: True for key in ARTICLE_COLUMNS},
            "tools.columns": TOOL_DEFAULTS,
            "appearance": {"density": "comfortable", "accent": "blue"}}


class PreferenceConflict(Exception):
    pass


def packed(record, section):
    values = dict(DEFAULTS[section])
    if record:
        values.update({k: v for k, v in (record.values or {}).items() if k in values})
    return {"values": values, "version": record.version if record else 0}


def all_preferences(user_id):
    records = {r.section: r for r in UserPreference.query.filter_by(user_id=user_id).all()}
    return {key: packed(records.get(key), key) for key in DEFAULTS}


def validate(section, values):
    if section not in DEFAULTS or not isinstance(values, dict) or not values or set(values) - set(DEFAULTS[section]):
        raise ValueError("Ungültiger Einstellungsbereich oder unbekannte Einstellung.")
    if section == "appearance":
        if "density" in values and values["density"] not in ("comfortable", "compact"):
            raise ValueError("Ungültige Tabellendichte.")
        if "accent" in values and values["accent"] not in ("blue", "teal", "violet"):
            raise ValueError("Ungültige Akzentfarbe.")
    elif any(type(value) is not bool for value in values.values()):
        raise ValueError("Spaltensichtbarkeit muss Ja oder Nein sein.")
    required = ("article_no",) if section == "articles.columns" else ("tool_no", "actions") if section == "tools.columns" else ()
    if any(values.get(key) is False for key in required):
        raise ValueError("Identifikation und erforderliche Aktionen bleiben sichtbar.")


def save_preferences(user_id, section, values, version):
    validate(section, values)
    if type(version) is not int or version < 0:
        raise ValueError("Ungültige Einstellungs-Version.")
    record = db.session.get(UserPreference, (user_id, section))
    if (record.version if record else 0) != version:
        raise PreferenceConflict()
    merged = packed(record, section)["values"]
    merged.update(values)
    if record is None:
        record = UserPreference(user_id=user_id, section=section, values=merged)
        db.session.add(record)
    else:
        record.values = merged
    db.session.commit()
    return packed(record, section)
