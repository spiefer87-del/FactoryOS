#!/usr/bin/env python3
"""Add nullable recipe references without rebuilding or rewriting existing tables."""
import sys
from pathlib import Path
from sqlalchemy import inspect, text
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db


def run_upgrade(check_only=False):
    inspector = inspect(db.engine)
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Dieses Upgrade erwartet SQLite.")
    additions = {"materials": {"ral_color": "VARCHAR(100)"},
                 "articles": {"masterbatch_id": "INTEGER REFERENCES materials(id)",
                              "masterbatch_percent": "FLOAT"}}
    existing = {}
    for table in additions:
        if not inspector.has_table(table):
            raise RuntimeError("Tabelle fehlt: " + table)
        existing[table] = {c["name"]: c for c in inspector.get_columns(table)}
        for key in additions[table]:
            if key in existing[table] and not existing[table][key]["nullable"]:
                raise RuntimeError("Neue Felder müssen optional sein: " + key)
    if not {"id", "material_id"}.issubset(existing["articles"]) or "material_type" not in existing["materials"]:
        raise RuntimeError("Voraussetzung fehlt: Artikel-Rohstoff- und Materialmodul.")
    if check_only:
        print("Masterbatch-Strukturprüfung erfolgreich. Keine Daten geändert.")
        return
    with db.engine.begin() as conn:
        for table, columns in additions.items():
            for key, datatype in columns.items():
                if key not in existing[table]:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {key} {datatype}"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_masterbatch_id ON articles(masterbatch_id)"))
        invalid = conn.execute(text("SELECT COUNT(*) FROM articles a LEFT JOIN materials m ON m.id=a.masterbatch_id WHERE a.masterbatch_id IS NOT NULL AND (m.id IS NULL OR m.material_type!='masterbatch')")).scalar()
        if invalid:
            raise RuntimeError("Ungültige Masterbatch-Zuordnungen vorhanden. Bitte prüfen.")
    print("Masterbatch-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_upgrade("--check" in sys.argv)
