#!/usr/bin/env python3
"""Idempotent database upgrade for the machine-booking production calendar."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.models import (
    ProductionCalendarException,
    ProductionCalendarSettings,
)
from factoryos.modules.production.services.calendar_service import (
    get_or_create_calendar_settings,
)


def run_upgrade():
    ProductionCalendarSettings.__table__.create(bind=db.engine, checkfirst=True)
    ProductionCalendarException.__table__.create(bind=db.engine, checkfirst=True)
    get_or_create_calendar_settings(commit=True)


def main():
    app = create_app()
    with app.app_context():
        run_upgrade()
    print("Produktionskalender-Upgrade erfolgreich abgeschlossen.")


if __name__ == "__main__":
    main()
