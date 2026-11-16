"""Physical tooling cannot be confirmed or set up on two machines concurrently."""
import runpy
import threading
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_machine_control_concurrency.py'))
app=fixture['app'];uid=fixture['uid']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import MachineToolState,SetupOperation
from factoryos.modules.production.services.machine_control_service import execute,snapshot
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state

with app.app_context():
    machines=[Machine(machine_no='MOUNT-RACE-'+str(i),machine_status='aktiv') for i in range(4)]
    tools=[Tool(tool_no='MOUNT-RACE-'+str(i),name='Tool') for i in range(2)]
    db.session.add_all([*machines,*tools]);db.session.commit();mids=[m.id for m in machines]


def race(setup=False):
    barrier=threading.Barrier(2);results=[];errors=[]
    def worker(index):
        with app.app_context():
            mid=mids[index+(2 if setup else 0)];rev=snapshot(mid)['revision']
            barrier.wait(timeout=10)
            try:
                if setup:execute(mid,uid,'setup',str(uuid4()),rev,tool_no='MOUNT-RACE-1')
                else:confirm_tool_state(mid,uid,str(uuid4()),rev,status='mounted',tool_no='MOUNT-RACE-0',reason='Vor Ort kontrolliert')
                results.append('ok')
            except ValueError:db.session.rollback();results.append('conflict')
            except Exception as error:db.session.rollback();errors.append(repr(error))
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(2)]
    for t in threads:t.start()
    for t in threads:t.join(timeout=25)
    assert not any(t.is_alive() for t in threads),'Deadlock'
    assert not errors,errors
    return sorted(results)

assert race()==['conflict','ok']
assert race(True)==['conflict','ok']
with app.app_context():
    assert MachineToolState.query.filter_by(tool_no='MOUNT-RACE-0',status='mounted').count()==1
    assert SetupOperation.query.filter_by(tool_no='MOUNT-RACE-1',outcome='active').count()==1
print('PASS: independent SQLite sessions serialize competing mount confirmations and setup starts for one physical tool; one winner, no duplicate stock/reservation or deadlock.')
