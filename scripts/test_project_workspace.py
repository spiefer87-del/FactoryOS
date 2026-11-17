"""Isolated synthetic project tests. Never opens production database."""
import runpy,tempfile
from pathlib import Path
from datetime import datetime,timedelta
from io import BytesIO
from PIL import Image
fixture=runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.tool_errors.models import ToolError
from factoryos.modules.projects.workspace_models import *
from factoryos.modules.projects.services.workspace_service import input_time,local_time
from factoryos.modules.production.models import TimeBooking
from scripts.upgrade_project_workspace import run_upgrade

with app.app_context():
    app.config['FACTORYOS_STORAGE_ROOT']=tempfile.mkdtemp(prefix='project_test_',dir=Path(__file__).resolve().parents[2])
    admin=db.session.merge(fixture['user']);tool=db.session.merge(fixture['tool'])
    old=Order(order_no='OLD-PROJECT',is_project=True,status='offen',project_leader_id=admin.id);db.session.add(old);db.session.commit()
    run_upgrade(True);run_upgrade();run_upgrade()
    assert db.session.get(Workspace,old.id) and db.session.get(Member,(old.id,admin.id))
    def client(user):
        c=app.test_client()
        with c.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True;session['access_csrf']='project-test'
        return c
    c=client(admin)
    assert c.get('/projects/').status_code==200
    assert c.post('/projects/create',data={}).status_code==400
    response=c.post('/projects/create',data={'access_csrf':'project-test','order_no':'P-TEST','description':'Werkzeug warten','tool_id':tool.id})
    assert response.status_code==303,response.get_data(as_text=True)
    item=Order.query.filter_by(order_no='P-TEST').one();pid=item.id
    assert c.get(f'/projects/{pid}').status_code==200
    def post(op,**data):
        version=db.session.get(Workspace,pid).version
        return c.post(f'/projects/{pid}/action',data=dict(access_csrf='project-test',version=version,op=op,**data))
    role=Role(name='project-worker',active=True);db.session.add(role)
    for perm in ('projects.view','projects.work'):
        role.permissions.append(Permission.query.filter_by(name=perm).one())
    worker=User(username='project-worker',password_hash='unused',active=True,role=role)
    outsider=User(username='project-outsider',password_hash='unused',active=True,role=role)
    db.session.add_all([worker,outsider]);db.session.commit()
    w=client(worker);o=client(outsider)
    assert w.get(f'/projects/{pid}').status_code==403
    assert b'P-TEST' not in w.get('/projects/').data
    assert post('member',user_id=worker.id).status_code==303
    assert w.get(f'/projects/{pid}').status_code==200
    assert b'P-TEST' in w.get('/projects/').data
    assert o.get(f'/projects/{pid}').status_code==403
    assert o.get('/projects/sources?project_id='+str(pid)+'&kind=error&q=FM').status_code==403
    assert w.post(f'/projects/{pid}/action',data=dict(access_csrf='project-test',version=db.session.get(Workspace,pid).version,op='archive',reason='No')).status_code==403
    assert post('task_add',title='Auswerfer prüfen',assignee_id=worker.id,due_date='2026-11-01').status_code==303
    task=Task.query.filter_by(project_id=pid).one()
    assert c.get(f'/projects/{pid}').status_code==200
    assert post('archive',reason='Abschluss').status_code==422
    error=ToolError(error_no='FM-PROJECT',tool_id=tool.id,description='Auswerfer klemmt',reported_by_id=admin.id);db.session.add(error);db.session.commit()
    found=c.get(f'/projects/sources?project_id={pid}&kind=error&q=FM-PROJECT');assert found.status_code==200 and found.json['results'][0]['id']==error.id
    assert post('link',kind='error',target_id=error.id).status_code==303
    link=Link.query.filter_by(project_id=pid,error_id=error.id).one()
    assert post('link',kind='error',target_id=error.id).status_code==409
    assert post('time_start',description='Wartung',link_id=link.id).status_code==303
    time=WorkTime.query.filter_by(project_id=pid).one()
    assert time.link_id==link.id
    assert post('time_start',description='Doppelt').status_code==422
    assert post('time_stop',time_id=time.id).status_code==303
    start=datetime.utcnow()-timedelta(days=1,hours=1);end=start+timedelta(hours=1)
    assert post('time_manual',description='Reparatur',start=input_time(start),end=input_time(end)).status_code==303
    assert post('time_manual',description='Überlappung',start=input_time(start),end=input_time(end)).status_code==422
    assert post('time_edit',time_id=time.id,start=input_time(start),end=input_time(end),description='Konflikt',reason='Test').status_code==422
    manual=WorkTime.query.filter_by(description='Reparatur').one()
    assert post('time_cancel',time_id=manual.id,reason='Fehleingabe').status_code==303
    assert manual.cancelled
    for wall in ('2026-03-29T02:30','2026-10-25T02:30'):
        try:local_time(wall);assert False
        except ValueError:pass
    assert local_time('2026-10-25T02:30','1')-local_time('2026-10-25T02:30','0')==timedelta(hours=1)
    part=dict(tool_id=tool.id,operation='remove',part_name='Auswerferstift',part_no='DIN-TEST',serial_no='S123',position='Nest 1',quantity='2',unit='Stück',reason='Verschlissen',disposition='Zur Aufarbeitung',occurred_at=input_time(datetime.utcnow()-timedelta(hours=1)),confirmed='yes',link_id=link.id)
    assert post('part',**{**part,'quantity':'-1'}).status_code==422
    before=db.session.get(Workspace,pid).version
    assert post('part',**part).status_code==303
    event=ToolPartEvent.query.filter_by(project_id=pid).one()
    assert c.post(f'/projects/{pid}/action',data=dict(access_csrf='project-test',version=before,op='part',**part)).status_code==409
    assert ToolPartEvent.query.filter_by(project_id=pid).count()==1
    assert post('part_reverse',event_id=event.id,reason='Falsche Menge').status_code==303
    assert post('part_reverse',event_id=event.id,reason='Nochmals').status_code==422
    assert c.get(f'/projects/tool/{tool.id}/history').status_code==200
    assert c.get(f'/masterdata/tools/{tool.id}').status_code==200
    image=BytesIO();Image.new('RGB',(2400,1600),'white').save(image,'JPEG');image.seek(0)
    assert post('report',text='Teil gewechselt; Funktionsprüfung folgt.',photo=(image,'test.jpg'),link_id=link.id).status_code==303
    assert Report.query.one().link_id==link.id
    photo=ReportPhoto.query.one();assert c.get(f'/projects/photo/{photo.id}').status_code==200
    assert o.get(f'/projects/photo/{photo.id}').status_code==403
    assert w.get(f'/projects/photo/{photo.id}').status_code==200
    invalid=post('report',text='Ungültiges Foto',photo=(BytesIO(b'bad'),'test.jpg'));assert invalid.status_code==422 and Report.query.count()==1
    assert post('task_status',task_id=task.id,status='done').status_code==303
    assert post('archive',reason='Arbeit abgeschlossen').status_code==303
    assert post('report',text='Nicht erlaubt').status_code==409
    assert c.get('/projects/?archive=1').status_code==200
    assert post('reopen',reason='Nacharbeit').status_code==303
    assert c.get(f'/projects/{pid}').status_code==200
    assert Audit.query.filter_by(project_id=pid).count()>10
    for table,key in (('orders',pid),('tool_errors',error.id),('tools',tool.id)):
        from sqlalchemy import text
        try:db.session.execute(text(f'DELETE FROM {table} WHERE id=:id'),{'id':key});db.session.commit();assert False,'Historie gelöscht'
        except __import__('sqlalchemy').exc.IntegrityError:db.session.rollback()
    print('PASS: additive/idempotent migration, personal isolation, assignment, source search/linking, task/archive gates, CSRF, time overlaps/DST/correction, tool part history/storno, stale/double submit, compressed photos and access checks, source deletion protection')
