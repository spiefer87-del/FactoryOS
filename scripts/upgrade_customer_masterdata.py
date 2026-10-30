#!/usr/bin/env python3
"""Add customers and nullable article ownership; never rebuild existing tables."""
import sys
from pathlib import Path
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.masterdata.customers.models import Customer


def run_upgrade(check_only=False):
    inspector = inspect(db.engine)
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("Dieses Upgrade ist ausschließlich für die konfigurierte SQLite-Datenbank vorgesehen.")
    if not inspector.has_table("articles"):
        raise RuntimeError("Tabelle articles fehlt. Keine Änderungen vorgenommen.")
    columns = {column["name"]: column for column in inspector.get_columns("articles")}
    if not {"id", "article_no", "article_name"}.issubset(columns):
        raise RuntimeError("Unerwartete Artikelstruktur. Keine Änderungen vorgenommen.")
    if "customer_id" in columns:
        if not columns["customer_id"]["nullable"]:
            raise RuntimeError("Vorhandene customer_id ist nicht optional. Upgrade abgebrochen.")
        if not inspector.has_table("customers"):
            raise RuntimeError("customer_id existiert ohne Kundentabelle. Bitte Struktur prüfen.")
    if inspector.has_table("customers"):
        actual = {c["name"] for c in inspector.get_columns("customers")}
        required = {c.name for c in Customer.__table__.columns}
        if not required.issubset(actual):
            raise RuntimeError("Vorhandene Kundentabelle entspricht nicht dem erwarteten Modell.")
    print("Datenbank:", db.engine.url.database)
    print("Artikelstruktur geprüft; vorhandene Artikel bleiben erhalten.")
    if check_only:
        print("Strukturprüfung erfolgreich. Keine Änderungen vorgenommen.")
        return
    Customer.__table__.create(bind=db.engine, checkfirst=True)
    with db.engine.begin() as connection:
        if "customer_id" not in columns:
            connection.execute(text(
                "ALTER TABLE articles ADD COLUMN customer_id INTEGER "
                "REFERENCES customers(id)"
            ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_articles_customer_id ON articles(customer_id)"
        ))
        orphans = connection.execute(text(
            "SELECT COUNT(*) FROM articles a LEFT JOIN customers c "
            "ON a.customer_id = c.id WHERE a.customer_id IS NOT NULL AND c.id IS NULL"
        )).scalar()
        if orphans:
            raise RuntimeError("Ungültige vorhandene Kundenreferenzen gefunden.")
    print("Kundenstamm-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_upgrade(check_only="--check" in sys.argv)
