"""Explicit, offline, once-only TEST reset. No application route calls this file."""
import argparse,hashlib,json,sqlite3
from datetime import datetime
from pathlib import Path

RESET_ID='factoryos-production-warehouse-test-reset-2026-11-17'
FULL=('warehouse_lines','warehouse_events','warehouse_reservations','warehouse_lots',
      'production_plan_entries','setup_operations','time_bookings','quantity_reports',
      'order_completions','machine_control_commands','machine_control_states')
CLOSED=('finished','fertig','closed','geschlossen','abgeschlossen','completed','cancelled','canceled','storniert','beendet')
TRIGGERS={f'immutable_{table}_{action}' for table in ('warehouse_events','warehouse_lines','warehouse_lots') for action in ('update','delete')}

def quote(name):return '"'+name.replace('"','""')+'"'
def fingerprint(connection):
    digest=hashlib.sha256()
    for statement in connection.iterdump():digest.update(statement.encode());digest.update(b'\n')
    return digest.hexdigest()

def prepare(connection,actor):
    tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required=set(FULL)|{'users','roles','orders','machines','machine_tool_states','sampling_orders','sampling_checks','erp_order_data','warehouse_locations','change_logs','warehouse_lock','machine_control_lock','production_planning_state'}
    if required-tables:raise ValueError('Tabellen fehlen; kein Reset: '+', '.join(sorted(required-tables)))
    user=connection.execute("SELECT u.id FROM users u JOIN roles r ON r.id=u.role_id WHERE u.username=? AND u.active=1 AND r.active=1 AND lower(trim(r.name))='admin'",(actor,)).fetchone()
    if not user:raise ValueError('Aktives Systemadministratorkonto fehlt: '+actor)
    connection.execute('CREATE TEMP TABLE reset_closed_orders (id INTEGER PRIMARY KEY)')
    connection.execute('INSERT INTO reset_closed_orders SELECT id FROM orders WHERE lower(trim(coalesce(status,\'\'))) IN ('+','.join('?' for _ in CLOSED)+')',CLOSED)
    connection.execute('INSERT OR IGNORE INTO reset_closed_orders SELECT order_id FROM order_completions')
    connection.execute("INSERT OR IGNORE INTO reset_closed_orders SELECT order_id FROM sampling_orders WHERE state='completed'")
    connection.execute('CREATE TEMP TABLE reset_closed_sampling (id INTEGER PRIMARY KEY)')
    connection.execute('INSERT INTO reset_closed_sampling SELECT id FROM sampling_orders WHERE order_id IN (SELECT id FROM reset_closed_orders)')
    selectors={table:'1' for table in FULL}
    selectors.update(orders='id IN (SELECT id FROM reset_closed_orders)',sampling_orders='id IN (SELECT id FROM reset_closed_sampling)',sampling_checks='sampling_id IN (SELECT id FROM reset_closed_sampling)',erp_order_data='order_id IN (SELECT id FROM reset_closed_orders)')
    # Refuse unknown dependent records rather than silently deleting other domains.
    for child in tables:
        for fk in connection.execute('PRAGMA foreign_key_list('+quote(child)+')'):
            parent,col,remote=fk[2],fk[3],fk[4] or 'id'
            if parent not in selectors:continue
            if (child,col,parent)==('sampling_orders','previous_id','sampling_orders'):continue
            sql='SELECT COUNT(*) FROM '+quote(child)+' WHERE '+quote(col)+' IN (SELECT '+quote(remote)+' FROM '+quote(parent)+' WHERE '+selectors[parent]+')'
            if child in selectors:sql+=' AND NOT ('+selectors[child]+')'
            if connection.execute(sql).fetchone()[0]:raise ValueError('Ungeklärter Fremdbezug in '+child+'.'+col+'. Reset wird nicht ausgeführt.')
    counts={table:connection.execute('SELECT COUNT(*) FROM '+quote(table)+' WHERE '+where).fetchone()[0] for table,where in selectors.items()}
    kept=[dict(r) for r in connection.execute('SELECT * FROM orders WHERE id NOT IN (SELECT id FROM reset_closed_orders) ORDER BY id')]
    machines=[r[0] for r in connection.execute('SELECT id FROM machines ORDER BY id')]
    links=connection.execute('SELECT COUNT(*) FROM sampling_orders WHERE id NOT IN (SELECT id FROM reset_closed_sampling) AND previous_id IN (SELECT id FROM reset_closed_sampling)').fetchone()[0]
    return dict(selectors=selectors,counts=counts,kept=kept,machines=machines,actor_id=user[0],sampling_links=links)

def run(database,*,actor='admin',apply=False,backup_directory=None,confirm='',offline=False):
    database=Path(database).resolve()
    if not database.is_file():raise ValueError('Vorhandene Datenbank fehlt: '+str(database))
    connection=sqlite3.connect(database.as_uri()+'?mode='+('rw' if apply else 'ro'),uri=True,timeout=15)
    connection.row_factory=sqlite3.Row
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        marker=connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='factoryos_test_reset_runs'").fetchone()
        if marker and connection.execute('SELECT 1 FROM factoryos_test_reset_runs WHERE id=?',(RESET_ID,)).fetchone():
            print('Dieser Testreset wurde bereits ausgeführt. Neue Daten bleiben unverändert.');return {'already_done':True}
        plan=prepare(connection,actor)
        print('Zu entfernen: '+json.dumps(plan['counts'],ensure_ascii=False))
        print('Offene Aufträge bleiben: '+json.dumps([r['order_no'] for r in plan['kept']],ensure_ascii=False))
        print('Maschinen danach bestätigt abgerüstet: '+str(len(plan['machines']))+'; eine neue Frei-Buchung je Maschine. Lagerplätze bleiben erhalten.')
        if not apply:print('Nur Vorschau. Keine Fachdaten geändert.');return plan['counts']
        if confirm!='RESET-TESTDATEN' or not offline or not backup_directory:raise ValueError('Explizite Bestätigung, gestoppter Dienst und Sicherungsordner erforderlich.')
        # TEMP preparation used a transaction but made no persistent changes.
        connection.commit()
        target_dir=Path(backup_directory).resolve()
        target_dir.mkdir(parents=True,exist_ok=False,mode=0o700)
        backup=target_dir/'factoryos.db'
        destination=sqlite3.connect(backup)
        try:connection.backup(destination);destination.close()
        finally:
            try:destination.close()
            except Exception:pass
        backup.chmod(0o600)
        saved=sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True)
        try:
            if saved.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Sicherung ist nicht konsistent.')
            saved_hash=fingerprint(saved)
        finally:saved.close()
        print('Geprüfte Sicherung: '+str(backup))
        connection.execute('BEGIN IMMEDIATE')
        if fingerprint(connection)!=saved_hash:raise ValueError('Datenbank seit Sicherung verändert. Keine Löschung.')
        connection.execute('DROP TABLE temp.reset_closed_sampling')
        connection.execute('DROP TABLE temp.reset_closed_orders')
        plan=prepare(connection,actor)  # Recheck actor, scope and dependencies under the write lock.
        connection.execute('PRAGMA defer_foreign_keys=ON')
        original_triggers=list(connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
        # Only the explicitly authorized test reset temporarily removes the known
        # warehouse DELETE/UPDATE guards, inside this same transaction.
        for trigger in original_triggers:
            if trigger['name'] in TRIGGERS:connection.execute('DROP TRIGGER '+quote(trigger['name']))
        connection.execute('UPDATE warehouse_events SET related_id=NULL,reversal_of=NULL')
        for table in FULL:connection.execute('DELETE FROM '+quote(table))
        connection.execute('UPDATE sampling_orders SET previous_id=NULL WHERE previous_id IN (SELECT id FROM reset_closed_sampling)')
        for table in ('sampling_checks','sampling_orders','erp_order_data','orders'):
            connection.execute('DELETE FROM '+quote(table)+' WHERE '+plan['selectors'][table])
        # Orders retained verbatim, including their imported source and sampling checks.
        after=[dict(r) for r in connection.execute('SELECT * FROM orders ORDER BY id')]
        if after!=plan['kept']:raise ValueError('Offene Aufträge wurden unerwartet verändert. Rollback.')
        now=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        # Read original versions from the verified backup, never reset them to zero.
        saved=sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True)
        try:controls=dict(saved.execute('SELECT machine_id,version FROM machine_control_states'))
        finally:saved.close()
        for machine_id in plan['machines']:
            connection.execute('INSERT INTO machine_control_states (machine_id,version,resume_process,resume_order_id,resume_tool_no) VALUES (?,?,NULL,NULL,NULL)',(machine_id,controls.get(machine_id,0)+1))
            connection.execute('INSERT INTO machine_tool_states (machine_id,status,tool_no,requires_confirmation,updated_at,updated_by_id) VALUES (?,\'empty\',NULL,0,?,?) ON CONFLICT(machine_id) DO UPDATE SET status=\'empty\',tool_no=NULL,requires_confirmation=0,updated_at=excluded.updated_at,updated_by_id=excluded.updated_by_id',(machine_id,now,plan['actor_id']))
            connection.execute("INSERT INTO time_bookings (user_id,machine_id,order_id,process,type,start_time,end_time,tool_no,comment) VALUES (?,?,NULL,'FREI','START',?,NULL,NULL,?)",(plan['actor_id'],machine_id,now,'Testreset: ohne Werkzeug / abgerüstet vom Administrator bestätigt'))
        for table in ('warehouse_lock','machine_control_lock','production_planning_state'):
            connection.execute('INSERT INTO '+quote(table)+' (id,version) VALUES (1,1) ON CONFLICT(id) DO UPDATE SET version=version+1')
        for trigger in original_triggers:
            if trigger['name'] in TRIGGERS:connection.execute(trigger['sql'])
        restored={r[0]:r[1] for r in connection.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'")}
        if any(restored.get(t['name'])!=t['sql'] for t in original_triggers):raise ValueError('Schutztrigger nicht vollständig wiederhergestellt. Rollback.')
        violations=list(connection.execute('PRAGMA foreign_key_check'))
        if violations:raise ValueError('Fremdschlüsselprüfung fehlgeschlagen; keine Änderung: '+str([tuple(r) for r in violations[:5]]))
        summary=dict(counts=plan['counts'],retained_orders=[r['order_no'] for r in plan['kept']],machines_empty=plan['machines'],detached_sampling_previous=plan['sampling_links'],backup=str(backup),backup_hash=saved_hash)
        connection.execute('CREATE TABLE IF NOT EXISTS factoryos_test_reset_runs (id TEXT PRIMARY KEY,created_at TEXT NOT NULL,summary TEXT NOT NULL)')
        connection.execute('INSERT INTO factoryos_test_reset_runs VALUES (?,?,?)',(RESET_ID,now,json.dumps(summary)))
        connection.execute("INSERT INTO change_logs (entity_type,entity_id,entity_name,action,category,user_id,changes,created_at) VALUES ('production',0,'Testphase zurückgesetzt','delete','production_warehouse_test_reset',?,?,?)",(plan['actor_id'],json.dumps({'test_reset':summary}),now))
        connection.commit()
        print('Testreset abgeschlossen. Offene Aufträge erhalten, Lager leer, alle Maschinen ohne Werkzeug bestätigt; Frei-Zeit läuft ab '+now+' UTC.')
        return summary
    except Exception:connection.rollback();raise
    finally:connection.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',default=str(Path(__file__).resolve().parents[1]/'instance/factoryos.db'));parser.add_argument('--actor',default='admin');parser.add_argument('--apply',action='store_true');parser.add_argument('--offline',action='store_true');parser.add_argument('--backup-directory');parser.add_argument('--confirm',default='')
    args=parser.parse_args();run(args.database,actor=args.actor,apply=args.apply,offline=args.offline,backup_directory=args.backup_directory,confirm=args.confirm)
