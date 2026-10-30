#!/usr/bin/env python3
"""Add an optional material foreign key without rebuilding the article table."""
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
    for table in ("articles", "materials", "customers"):
        if not inspector.has_table(table):
            raise RuntimeError("Voraussetzung fehlt: Tabelle " + table)
    columns = {c["name"]: c for c in inspector.get_columns("articles")}
    if not {"id", "article_no", "customer_id"}.issubset(columns):
        raise RuntimeError("Artikelstruktur entspricht nicht dem erwarteten Kunden-Patch.")
    if "material_id" in columns and not columns["material_id"]["nullable"]:
        raise RuntimeError("material_id muss optional sein.")
    if check_only:
        print("Strukturprüfung erfolgreich; keine Änderungen vorgenommen.")
        return
    with db.engine.begin() as conn:
        if "material_id" not in columns:
            conn.execute(text("ALTER TABLE articles ADD COLUMN material_id INTEGER REFERENCES materials(id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_material_id ON articles(material_id)"))
        if conn.execute(text("SELECT COUNT(*) FROM articles a LEFT JOIN materials m ON a.material_id=m.id WHERE a.material_id IS NOT NULL AND m.id IS NULL")).scalar():
            raise RuntimeError("Ungültige Rohstoffreferenzen gefunden.")
    print("Artikel-Rohstoff-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_upgrade("--check" in sys.argv)
