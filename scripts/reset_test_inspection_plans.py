#!/usr/bin/env python3
"""One-off, explicitly requested reset. Requires a matching offline DB backup."""
import sys,sqlite3
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from factoryos import create_app
from factoryos.extensions import db
from factoryos.modules.article_defects.models import InspectionResetRun
from factoryos.core.models.change_log import ChangeLog
RESET_ID='factoryos-test-plans-reset-2026-11-17'
TABLES=('qm_checks','qm_characteristics','qm_gauge_checks','qm_section_images','qm_dimension_snippets','qm_change_logs','qm_sections','qm_plan_versions','qm_plans')

def run_reset(backup=None,apply=False):
    inspector=inspect(db.engine)
    if inspector.has_table('inspection_reset_runs') and db.session.get(InspectionResetRun,RESET_ID):
        print('Prüfplan-Testreset wurde bereits ausgeführt. Neue Prüfpläne bleiben erhalten.');return {}
    tables=[table for table in TABLES if inspector.has_table(table)]
    counts={table:db.session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one() for table in tables}
    print('Betroffen: '+str(counts))
    # Stop if an extension introduced external references not accounted for here.
    for table in inspector.get_table_names():
        if table in TABLES:continue
        for foreign in inspector.get_foreign_keys(table):
            if foreign.get('referred_table') in TABLES:raise RuntimeError('Zusätzlicher Prüfplanbezug muss zuerst geklärt werden: '+table)
    if not apply:print('Nur Vorschau. Keine Änderungen.');return counts
    if not backup:raise ValueError('Passende Datenbanksicherung erforderlich.')
    path=Path(backup).resolve()
    source=db.engine.url.database
    if not path.is_file() or (source and path==Path(source).resolve()):raise ValueError('Separate vorhandene Datenbanksicherung erforderlich.')
    connection=sqlite3.connect('file:'+quote(str(path))+'?mode=ro',uri=True)
    try:
        if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Sicherung ist nicht konsistent.')
        saved={table:connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in tables}
        if saved!=counts:raise ValueError('Sicherung passt nicht zum aktuellen Prüfplanbestand. Keine Löschung.')
        for table in tables:
            live=[tuple(row) for row in db.session.execute(text(f'SELECT * FROM {table} ORDER BY id'))]
            archived=connection.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
            if live!=archived:raise ValueError('Sicherungsinhalt stimmt nicht mit dem aktuellen Prüfplanbestand überein. Keine Löschung.')
    finally:connection.close()
    for table in tables:db.session.execute(text(f'DELETE FROM {table}'))
    db.session.add(InspectionResetRun(id=RESET_ID,backup=str(path),counts=counts))
    db.session.add(ChangeLog(entity_type='quality',entity_id=0,entity_name='Prüfplan-Testphase',action='delete',category='inspection_test_reset',user_id=None,changes={'reset':{'old':counts,'new':{'plans':0,'backup':str(path),'reset_id':RESET_ID}}}))
    db.session.commit();db.session.expire_all()
    print('Alle Prüfpläne einschließlich Revisionen/Modulen/Prüfplanhistorie entfernt. Andere Fachdaten unverändert. Mediendateien bleiben für Wiederherstellung erhalten.')
    return counts

if __name__=='__main__':
    app=create_app()
    with app.app_context():
        import argparse
        parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--backup');args=parser.parse_args()
        try:run_reset(args.backup,args.apply)
        except Exception:db.session.rollback();raise
