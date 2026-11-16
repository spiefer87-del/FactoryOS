"""Independent SQLite sessions: concurrent completion and start/complete race."""
import runpy
import threading
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_machine_control_concurrency.py'))
app=fixture['app'];uid=fixture['uid']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import OrderCompletion,TimeBooking
from factoryos.modules.production.services.order_completion_service import complete_order,completion_context
from factoryos.modules.production.services.machine_control_service import execute,snapshot

with app.app_context():
    orders=[Order(order_no='CLOSE-RACE-'+str(i),target_qty=100,cycle_time_s=30) for i in range(2)]
    machine=Machine(machine_no='CLOSE-RACE',machine_status='aktiv')
    db.session.add_all([*orders,machine]);db.session.commit()
    ids=[o.id for o in orders];mid=machine.id


def race(start=False):
    barrier=threading.Barrier(2);results=[];errors=[]
    def worker(index):
        with app.app_context():
            order=db.session.get(Order,ids[1 if start else 0])
            rev=completion_context(order)['revision'];machine_rev=snapshot(mid)['revision']
            barrier.wait(timeout=10)
            try:
                if start and index==1:
                    execute(mid,uid,'start',str(uuid4()),machine_rev,order_id=order.id);results.append('started')
                else:
                    complete_order(order.id,uid,str(uuid4()),rev,good_qty='100',scrap_qty='0',confirmed=True);results.append('closed')
            except ValueError:db.session.rollback();results.append('conflict')
            except Exception as error:db.session.rollback();errors.append(repr(error))
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(2)]
    for thread in threads:thread.start()
    for thread in threads:thread.join(timeout=25)
    assert not any(t.is_alive() for t in threads),'Deadlock'
    assert not errors,errors
    return sorted(results)

assert race()==['closed','conflict']
assert race(True) in (['closed','conflict'],['conflict','started'])
with app.app_context():
    assert OrderCompletion.query.filter_by(order_id=ids[0]).count()==1
    assert OrderCompletion.query.filter_by(order_id=ids[1]).count()+TimeBooking.query.filter_by(order_id=ids[1],end_time=None).count()==1
print('PASS: concurrent completions produce one immutable close, start vs office completion has one winner; independent SQLite sessions, no lost state or deadlock.')
