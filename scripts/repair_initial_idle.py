#!/usr/bin/env python3
"""Explicit maintenance repair, not a web read/startup side effect."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.production.services.idle_recording_service import repair_missing_idle


if __name__=='__main__':
    app=create_app()
    with app.app_context():
        try:
            preview='--check' in sys.argv
            result=repair_missing_idle(check_only=preview)
            print(('Vorschau: ' if preview else 'Nachgetragen: ')+str(len(result['created']))+' initiale Leerlaufbuchungen.')
            for item in result['created']:print(item['machine_no']+' · '+item['start_at']+' UTC · '+item['basis'])
            print('Unverändert/übersprungen: '+str(len(result['skipped'])))
            for item in result['skipped']:print('Maschine #'+str(item['machine_id'])+': '+item['reason'])
        except Exception:
            db.session.rollback()
            print('Nachtrag fehlgeschlagen; Transaktion zurückgerollt. Bitte Fehlerursache prüfen.')
            raise
