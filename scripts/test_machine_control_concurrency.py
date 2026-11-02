"""Concurrent commands using independent SQLAlchemy sessions and temporary SQLite."""
import os
import sys
import types
import secrets
import tempfile
import threading
from uuid import uuid4
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault("FACTORYOS_SECRET_KEY",secrets.token_hex(48))
sys.modules["cv2"]=types.ModuleType("cv2")
from factoryos.config import Config
test_dir=Path(tempfile.mkdtemp(prefix="machine_control_concurrency_",dir=ROOT.parent))
Config.SQLALCHEMY_DATABASE_URI="sqlite:///"+str(test_dir/"test.db")
Config.SQLALCHEMY_ENGINE_OPTIONS={"connect_args":{"timeout":10}}
from factoryos import create_app
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.production.models import TimeBooking,MachineControlCommand,MachineControlState,MachineControlLock
from factoryos.modules.production.services.machine_control_service import execute,snapshot,ControlConflict
with redirect_stdout(StringIO()):app=create_app()
with app.app_context():
    db.create_all()
    # Exercise the actual upgrade from an existing schema without control tables.
    from sqlalchemy import inspect
    from scripts.upgrade_machine_control import run_upgrade
    for model in (MachineControlCommand,MachineControlState,MachineControlLock):
        model.__table__.drop(bind=db.engine)
    run_upgrade(True)
    assert not inspect(db.engine).has_table("machine_control_commands")
    run_upgrade();run_upgrade()
    user=User(username="concurrency-admin",password_hash="unused",active=True,role=Role(name="admin",active=True))
    machines=[Machine(machine_no=f"CONCURRENT-{i}",machine_status="aktiv") for i in range(4)]
    orders=[Order(order_no=f"CONCURRENT-{i}",target_qty=100,cycle_time_s=30) for i in range(2)]
    db.session.add_all([user,*machines,*orders]);db.session.commit()
    uid=user.id;mids=[m.id for m in machines];oids=[o.id for o in orders]

def race(machine_ids,order_id,same_command=False):
    barrier=threading.Barrier(2);results=[];errors=[];shared_id=str(uuid4())
    def worker(mid):
        with app.app_context():
            rev=snapshot(mid)["revision"]
            barrier.wait(timeout=10)
            try:
                _,replayed=execute(mid,uid,"start",shared_id if same_command else str(uuid4()),rev,order_id=order_id)
                results.append("replayed" if replayed else "started")
            except ControlConflict:
                db.session.rollback();results.append("conflict")
            except Exception as exc:
                db.session.rollback();errors.append(repr(exc))
    threads=[threading.Thread(target=worker,args=(mid,)) for mid in machine_ids]
    for t in threads:t.start()
    for t in threads:t.join(timeout=20)
    assert not any(t.is_alive() for t in threads),"Concurrent request deadlocked"
    assert not errors,errors
    return sorted(results)

assert race(mids[:2],oids[0])==["conflict","started"]
assert race([mids[2],mids[2]],oids[1],True)==["replayed","started"]
with app.app_context():
    assert TimeBooking.query.filter_by(process="PROD",end_time=None).count()==2
    assert MachineControlCommand.query.count()==2
    assert TimeBooking.query.filter_by(order_id=oids[0],end_time=None).count()==1
    assert TimeBooking.query.filter_by(order_id=oids[1],end_time=None).count()==1
print("PASS: two machines cannot claim the same order concurrently; simultaneous identical UUID creates one booking and one receipt; independent SQLite sessions, no deadlock.")
