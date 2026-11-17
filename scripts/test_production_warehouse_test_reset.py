import runpy,sqlite3,tempfile
from pathlib import Path
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
from factoryos.extensions import db
from factoryos.modules.orders.models import Order
from scripts.upgrade_inventory import run_upgrade
from scripts.reset_production_warehouse_tests import run,RESET_ID
app=fixture['app']

with app.app_context():
    run_upgrade()
    closed=Order(order_no='RESET-CLOSED',status='finished');opened=Order(order_no='RESET-OPEN',status='open',target_qty=123)
    db.session.add_all([closed,opened]);db.session.commit()
    root=Path(tempfile.mkdtemp(prefix='test_full_reset_',dir=Path(__file__).resolve().parents[2]));database=root/'fixture.db'
    raw=db.engine.raw_connection();target=sqlite3.connect(database);raw.driver_connection.backup(target);target.close();raw.close()

c=sqlite3.connect(database);c.row_factory=sqlite3.Row
article=c.execute('SELECT id FROM articles LIMIT 1').fetchone()[0]
actor=c.execute("SELECT id FROM users WHERE username='test'").fetchone()[0]
closed_id=c.execute("SELECT id FROM orders WHERE order_no='RESET-CLOSED'").fetchone()[0]
c.execute("INSERT INTO warehouse_locations(code,description) VALUES ('TEST-LOCATION','Erhalten')")
c.execute("INSERT INTO warehouse_lots (order_id,article_id,article_no,article_name,batch,quantity,origin,created_at) VALUES (?,?,'A001','Test','TEST',10,'production','2026-11-16')",(closed_id,article))
lot=c.execute('SELECT MAX(id) FROM warehouse_lots').fetchone()[0];location=c.execute('SELECT MAX(id) FROM warehouse_locations').fetchone()[0]
c.execute("INSERT INTO warehouse_reservations (lot_id,location_id,quantity,remaining,state,reference) VALUES (?,?,10,10,'reserved','TEST')",(lot,location))
reservation=c.execute('SELECT MAX(id) FROM warehouse_reservations').fetchone()[0]
c.execute("INSERT INTO warehouse_events (command_id,payload_hash,kind,lot_id,reservation_id,quantity,transfer_effect,reason,user_id,created_at,details) VALUES ('TEST-EVENT','hash','receive',?,?,10,0,'TEST',?,'2026-11-16','{}')",(lot,reservation,actor))
event=c.execute('SELECT MAX(id) FROM warehouse_events').fetchone()[0]
c.execute("INSERT INTO warehouse_events (command_id,payload_hash,kind,lot_id,quantity,transfer_effect,related_id,reversal_of,reason,user_id,created_at,details) VALUES ('TEST-REVERSAL','hash','reverse',?,10,0,?,?,'TEST',?,'2026-11-16','{}')",(lot,event,event,actor))
c.execute("INSERT INTO warehouse_lines (event_id,lot_id,location_id,status,quantity) VALUES (?,?,?,'blocked',10)",(event,lot,location))
machine=c.execute('SELECT id FROM machines LIMIT 1').fetchone()[0]
c.execute("INSERT INTO quantity_reports (user_id,order_id,machine_id,good_qty,scrap_qty,created_at) VALUES (?,?,?,10,2,'2026-11-16')",(actor,closed_id,machine))
c.execute("INSERT INTO time_bookings (user_id,machine_id,order_id,process,type,tool_no,start_time,end_time) VALUES (?,?,?,'RUEST','START','W001','2026-11-16 13:48:24','2026-11-16 13:48:35')",(actor,machine,closed_id))
booking=c.execute('SELECT MAX(id) FROM time_bookings').fetchone()[0]
c.execute("INSERT INTO setup_operations (machine_id,order_id,tool_no,kind,outcome,started_at,ended_at,started_by_id,start_booking_id) VALUES (?,?,'W001','RUEST','completed','2026-11-16 13:48:24','2026-11-16 13:48:54',?,?)",(machine,closed_id,actor,booking))
c.execute("INSERT INTO production_plan_entries (machine_id,order_id,position,state,setup_minutes,created_by_id,updated_by_id,created_at,updated_at,started_booking_id) VALUES (?,?,0,'started',0,?,?,'2026-11-16','2026-11-16',?)",(machine,closed_id,actor,actor,booking))
c.commit()
original=dict(c.execute("SELECT * FROM orders WHERE order_no='RESET-OPEN'").fetchone())
counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('articles','tools','machines','warehouse_locations')}
before=c.execute('SELECT COUNT(*) FROM time_bookings').fetchone()[0];c.close()
run(database,actor='test')
c=sqlite3.connect(database);assert c.execute('SELECT COUNT(*) FROM time_bookings').fetchone()[0]==before;c.close()
try:run(database,actor='test',apply=True,offline=True,confirm='wrong',backup_directory=root/'bad');assert False
except ValueError:pass
# A retained unknown dependency must stop before making a backup or deleting anything.
c=sqlite3.connect(database);c.execute('CREATE TABLE reset_unknown_ref (id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES orders(id))');c.execute('INSERT INTO reset_unknown_ref(order_id) VALUES (?)',(closed_id,));c.commit();c.close()
try:run(database,actor='test',apply=True,offline=True,confirm='RESET-TESTDATEN',backup_directory=root/'blocked');assert False
except ValueError:pass
c=sqlite3.connect(database);assert c.execute('SELECT COUNT(*) FROM warehouse_lots').fetchone()[0]==1;c.execute('DROP TABLE reset_unknown_ref');c.commit();c.close()
# Inject a late failure after deletes to verify the whole transaction rolls back.
failed=root/'failed.db';source=sqlite3.connect(database);copy=sqlite3.connect(failed);source.backup(copy);source.close()
copy.execute("CREATE TRIGGER test_fail_idle BEFORE INSERT ON time_bookings WHEN NEW.process='FREI' BEGIN SELECT RAISE(ABORT,'Injected reset failure'); END");copy.commit();copy.close()
try:run(failed,actor='test',apply=True,offline=True,confirm='RESET-TESTDATEN',backup_directory=root/'failed_backup');assert False
except sqlite3.IntegrityError:pass
copy=sqlite3.connect(failed)
assert copy.execute('SELECT COUNT(*) FROM warehouse_lots').fetchone()[0]==1
assert copy.execute("SELECT id FROM orders WHERE order_no='RESET-CLOSED'").fetchone()
assert len(list(copy.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'immutable_%'")))==6
assert not copy.execute("SELECT name FROM sqlite_master WHERE name='factoryos_test_reset_runs'").fetchone();copy.close()
result=run(database,actor='test',apply=True,offline=True,confirm='RESET-TESTDATEN',backup_directory=root/'backup')
c=sqlite3.connect(database);c.row_factory=sqlite3.Row
assert not c.execute("SELECT id FROM orders WHERE order_no='RESET-CLOSED'").fetchone()
assert dict(c.execute("SELECT * FROM orders WHERE order_no='RESET-OPEN'").fetchone())==original
for t in ('warehouse_events','warehouse_lines','warehouse_lots','warehouse_reservations','quantity_reports','order_completions','setup_operations','production_plan_entries','machine_control_commands'):assert c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]==0,t
for t,count in counts.items():assert c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]==count
assert c.execute('SELECT COUNT(*) FROM time_bookings').fetchone()[0]==counts['machines']
assert not c.execute("SELECT id FROM time_bookings WHERE process!='FREI' OR tool_no IS NOT NULL OR order_id IS NOT NULL OR end_time IS NOT NULL").fetchone()
assert not c.execute("SELECT machine_id FROM machine_tool_states WHERE status!='empty' OR tool_no IS NOT NULL OR requires_confirmation!=0").fetchone()
assert not list(c.execute('PRAGMA foreign_key_check'))
assert len(list(c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'immutable_%'")))==6
c.execute('SAVEPOINT verify_immutable')
c.execute("INSERT INTO warehouse_lots (article_id,article_no,article_name,batch,quantity,origin,created_at) VALUES (?,'A001','Test','NEW',1,'opening','2026-11-17')",(article,))
new_lot=c.execute('SELECT MAX(id) FROM warehouse_lots').fetchone()[0]
for sql in ('UPDATE warehouse_lots SET quantity=2 WHERE id=?','DELETE FROM warehouse_lots WHERE id=?'):
    try:c.execute(sql,(new_lot,));assert False,'Lagerschutz nicht aktiv'
    except sqlite3.IntegrityError:pass
c.execute('ROLLBACK TO verify_immutable');c.execute('RELEASE verify_immutable')
c.execute("INSERT INTO orders (order_no,status) VALUES ('NEW-AFTER-RESET','open')");c.commit();c.close()
assert run(database,actor='test',apply=True,offline=True,confirm='RESET-TESTDATEN',backup_directory=root/'repeat')['already_done']
c=sqlite3.connect(database);assert c.execute("SELECT id FROM orders WHERE order_no='NEW-AFTER-RESET'").fetchone();c.close()
backup=sqlite3.connect(root/'backup/factoryos.db');assert backup.execute("SELECT id FROM orders WHERE order_no='RESET-CLOSED'").fetchone();assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok';backup.close()
print('PASS: preview, explicit confirmation, unknown dependency stop, verified backup, closed orders removed/open orders unchanged, warehouse and quantities cleared, masterdata/locations preserved, all machines empty with new idle timelines, original immutable triggers restored, FK integrity and once-only guard')
