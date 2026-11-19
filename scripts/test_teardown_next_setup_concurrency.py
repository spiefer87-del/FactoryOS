"""Independent sessions: direct next setup, empty choice and tool contention."""
import runpy,threading
from pathlib import Path
from uuid import uuid4
fixture=runpy.run_path(str(Path(__file__).with_name('test_machine_control_concurrency.py')))
app=fixture['app'];uid=fixture['uid']
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking,SetupOperation
from factoryos.modules.production.services.machine_control_service import execute,snapshot
from factoryos.modules.production.services.tool_mount_service import confirm_tool_state

def prepare(name):
    machine=Machine(machine_no=name,machine_status='aktiv');old=Tool(tool_no=name+'-OLD',name='Alt')
    db.session.add_all([machine,old]);db.session.commit()
    mid=machine.id
    confirm_tool_state(mid,uid,str(uuid4()),snapshot(mid)['revision'],status='mounted',tool_no=old.tool_no,reason='Bestand für Paralleltest geprüft')
    execute(mid,uid,'unsetup',str(uuid4()),snapshot(mid)['revision'])
    return mid

def race(kind):
    with app.app_context():
        name='TEARDOWN-RACE-'+kind;new=Tool(tool_no=name+'-NEW',name='Neu');db.session.add(new);db.session.commit();number=new.tool_no
        one=prepare(name+'-A');two=prepare(name+'-B') if kind=='tool' else one
        revisions={mid:snapshot(mid)['revision'] for mid in (one,two)}
    barrier=threading.Barrier(2);results=[];errors=[];shared=str(uuid4())
    def worker(index,mid):
        with app.app_context():
            barrier.wait(timeout=10)
            mode='free' if kind=='choice' and index==1 else 'setup'
            try:
                _,replay=execute(mid,uid,'finish_setup',shared if kind=='replay' else str(uuid4()),revisions[mid],
                    finish_mode=mode,tool_no=number if mode=='setup' else None)
                results.append('replayed' if replay else 'saved')
            except ValueError:db.session.rollback();results.append('conflict')
            except Exception as exc:db.session.rollback();errors.append(repr(exc))
    threads=[threading.Thread(target=worker,args=(i,mid)) for i,mid in enumerate((one,two))]
    for t in threads:t.start()
    for t in threads:t.join(timeout=25)
    assert not errors and not any(t.is_alive() for t in threads),(errors,results)
    assert sorted(results)==(['replayed','saved'] if kind=='replay' else ['conflict','saved']),results
    with app.app_context():
        assert SetupOperation.query.filter(SetupOperation.machine_id.in_((one,two)),SetupOperation.kind=='ABRUEST',SetupOperation.outcome=='completed').count()==1
        if kind=='tool':
            assert SetupOperation.query.filter_by(tool_no=number,outcome='active').count()==1
            assert SetupOperation.query.filter(SetupOperation.machine_id.in_((one,two)),SetupOperation.kind=='ABRUEST',SetupOperation.outcome=='active').count()==1
        for mid in set((one,two)):
            rows=TimeBooking.query.filter_by(machine_id=mid).order_by(TimeBooking.id).all()
            active=[r for r in rows if r.end_time is None]
            assert len(active)==1
            if active[0].process!='ABRUEST':
                assert len(rows)==3 and rows[-2].end_time==rows[-1].start_time
                assert active[0].process in ('RUEST','FREI')

for kind in ('replay','choice','tool'):race(kind)
print('PASS: identical handover UUID saved once, competing setup/free choices have one winner, two machines cannot reserve the same next tool, losing teardown remains unmodified, exact adjacent boundaries and no deadlock')
