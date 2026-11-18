"""Simultaneous setup decisions serialize without duplicate production or idle."""
import runpy,threading
from pathlib import Path
from uuid import uuid4
fixture=runpy.run_path(str(Path(__file__).with_name('test_machine_control_concurrency.py')))
app=fixture['app'];uid=fixture['uid']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking,SetupOperation,BookingIdleContext
from factoryos.modules.production.services.machine_control_service import execute,snapshot

def race(same_command):
    with app.app_context():
        name='WAIT-RACE-'+str(same_command)
        machine=Machine(machine_no=name,machine_status='aktiv');tool=Tool(tool_no=name,name=name)
        order=Order(order_no=name,tool_no=name,target_qty=100,cycle_time_s=60)
        db.session.add_all([machine,tool,order]);db.session.commit();mid=machine.id;oid=order.id
        execute(mid,uid,'setup',str(uuid4()),snapshot(mid)['revision'],order_id=oid)
        expected=snapshot(mid)['revision']
    barrier=threading.Barrier(2);results=[];errors=[];shared=str(uuid4())
    def worker(index):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                mode='start' if same_command or index==0 else 'wait'
                _,replayed=execute(mid,uid,'finish_setup',shared if same_command else str(uuid4()),expected,
                    order_id=oid,finish_mode=mode,wait_reason='material' if mode=='wait' else None)
                results.append('replayed' if replayed else 'saved')
            except ValueError:db.session.rollback();results.append('conflict')
            except Exception as exc:db.session.rollback();errors.append(repr(exc))
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(2)]
    for thread in threads:thread.start()
    for thread in threads:thread.join(timeout=25)
    assert not errors and not any(t.is_alive() for t in threads),(errors,results)
    assert sorted(results)==(['replayed','saved'] if same_command else ['conflict','saved']),results
    with app.app_context():
        assert SetupOperation.query.filter_by(machine_id=mid,outcome='completed').count()==1
        active=TimeBooking.query.filter_by(machine_id=mid,end_time=None).all()
        assert len(active)==1 and active[0].process in ('PROD','FREI')
        assert TimeBooking.query.filter_by(machine_id=mid).count()==2
        if active[0].process=='PROD':assert active[0].idle_context is None
        else:assert active[0].idle_context.reason_code=='material' and active[0].order_id==oid

race(True);race(False)
print('PASS: independent SQLite sessions; repeated direct-start UUID replays once, competing start/wait decisions have one winner, one completed setup and one active interval, no duplicate production/idle and no deadlock')
