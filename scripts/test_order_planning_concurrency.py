"""Independent SQLite sessions: plan/plan and plan/manual-start races."""
import runpy
import threading
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_machine_control_concurrency.py"))
app=fixture["app"]
uid=fixture["uid"]
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import ProductionPlanEntry,TimeBooking
from factoryos.modules.production.services.planning_service import planning_version,modify_plan
from factoryos.modules.production.services.machine_control_service import execute,snapshot,ControlConflict

with app.app_context():
    machines=[Machine(machine_no=f"PLANNING-RACE-{i}",machine_status="aktiv") for i in range(4)]
    orders=[Order(order_no=f"PLANNING-RACE-{i}",target_qty=100,cycle_time_s=30) for i in range(2)]
    db.session.add_all([*machines,*orders]);db.session.commit()
    mids=[m.id for m in machines];oids=[o.id for o in orders]

def race(start_race=False):
    barrier=threading.Barrier(2);results=[];errors=[]
    def worker(index):
        with app.app_context():
            mid=mids[index+(2 if start_race else 0)]
            version=planning_version();revision=snapshot(mid)["revision"]
            barrier.wait(timeout=10)
            try:
                if start_race and index==1:
                    execute(mid,uid,"start",str(uuid4()),revision,order_id=oids[1]);results.append("started")
                else:
                    modify_plan(uid,version,"add",mid,order_id=oids[1 if start_race else 0]);results.append("planned")
            except ValueError:
                db.session.rollback();results.append("conflict")
            except Exception as exc:
                db.session.rollback();errors.append(repr(exc))
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(2)]
    for t in threads:t.start()
    for t in threads:t.join(timeout=20)
    assert not any(t.is_alive() for t in threads),"Deadlocked planning request"
    assert not errors,errors
    return sorted(results)

assert race()==["conflict","planned"]
assert race(True) in (["conflict","planned"],["conflict","started"])
with app.app_context():
    assert ProductionPlanEntry.query.filter_by(order_id=oids[0],state="queued").count()==1
    planned=ProductionPlanEntry.query.filter_by(order_id=oids[1],state="queued").count()
    active=TimeBooking.query.filter_by(order_id=oids[1],end_time=None).count()
    assert planned+active==1
print("PASS: competing planners cannot duplicate an order or lose changes; plan vs manual start cannot assign the same order to different machines; independent SQLite sessions, no deadlock.")
