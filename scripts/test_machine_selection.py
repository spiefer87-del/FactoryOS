"""Master-only tool acknowledgement and explicit cross-machine sampling preparation."""
import copy
import json
import re
import runpy
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.sampling.models import SamplingOrder,SamplingCheck
from factoryos.modules.production.models import TimeBooking,ProductionPlanEntry,MachineControlState
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.production.services.machine_control_service import execute,snapshot,current_booking
from factoryos.modules.production.services.order_completion_service import complete_order,completion_context
from factoryos.modules.production.services.control_selection_service import tool_proposal,stock_proposal
from factoryos.modules.production.services.tool_mount_service import tool_snapshot


def hidden(html,key):return re.search(r'name="'+key+r'"[^>]*value="([^"]*)"',html).group(1)
def boot(html):return json.loads(re.search(r'<script type="application/json" id="control-selection-data">(.*?)</script>',html,re.S).group(1))

with app.app_context():
    user=db.session.merge(fixture['user'])
    m=Machine(machine_no='SEL-M1',machine_status='aktiv');other=Machine(machine_no='SEL-M2',machine_status='aktiv')
    ta=Tool(tool_no='SEL-1',name='Werkzeug Eins');tb=Tool(tool_no='SEL-2',name='Werkzeug Zwei')
    article=Article(article_no='SEL-ART',article_name='Artikel',tools=[ta])
    order=Order(order_no='SEL-PROD',article='SEL-ART',tool_no='SEL-1',target_qty=100,cycle_time_s=30)
    db.session.add_all([m,other,ta,tb,article,order]);db.session.flush()
    sample=SamplingOrder(order=Order(order_no='SEL-SAMPLE',article='SEL-ART',tool_no='SEL-1',target_qty=10,cycle_time_s=30,status='gesperrt'),
        reason='initial',state='draft',tool=ta,machine=other,created_by_id=user.id,data={'do_not_change':'QC'},snapshot={'machine':{'number':'SEL-M2'}},
        checks=[SamplingCheck(key='internal',status='open')])
    unassigned=SamplingOrder(order=Order(order_no='SEL-UNASSIGNED',tool_no='SEL-1',target_qty=1,cycle_time_s=30,status='gesperrt'),
        reason='initial',state='rework',tool=ta,created_by_id=user.id,data={},snapshot={})
    done=SamplingOrder(order=Order(order_no='SEL-COMPLETED',status='fertig'),reason='initial',state='completed',created_by_id=user.id,data={},snapshot={})
    db.session.add_all([sample,unassigned,done]);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    path=f'/production/machine/{m.id}/control'
    html=client.get(path+'?order_id='+str(sample.order_id)).get_data(as_text=True)
    assert 'SEL-SAMPLE' in html and 'SEL-UNASSIGNED' in html and 'SEL-COMPLETED' not in html
    assert 'Für SEL-M2 vorgesehen' in html and 'Aus Auftrag übernehmen' not in html
    data=boot(html)
    assert data['orders'][str(sample.order_id)]['proposal']['number']=='SEL-1'
    assert not data['orders'][str(sample.order_id)]['ready']
    assert hidden(html,'tool_confirmation_no')=='SEL-1'
    assert sample.machine_id==other.id and sample.state=='draft' # GET is read-only
    def command(action,order_id='',tool='SEL-1',confirmed=True,confirmation_no=None):
        page=client.get(path).get_data(as_text=True)
        return client.post(path,data=dict(access_csrf=hidden(page,'access_csrf'),revision=hidden(page,'revision'),command_id=hidden(page,'command_id'),
            action=action,order_id=order_id,tool_no=tool,tool_confirmed='yes' if confirmed else '',tool_confirmation_no=tool if confirmation_no is None else confirmation_no))
    n=TimeBooking.query.count()
    assert command('setup',tool='UNKNOWN').status_code==400
    assert command('setup',tool='SEL-1',confirmed=False).status_code==400
    assert command('setup',tool='SEL-1',confirmation_no='SEL-2').status_code==400
    assert command('start',order_id=sample.order_id).status_code==400
    assert TimeBooking.query.count()==n and sample.state=='draft'
    # Foreign machine requires an extra explicit acknowledgement, then stays preparation only.
    prepare=data['orders'][str(sample.order_id)]['prepare_url']
    page=client.get(prepare).get_data(as_text=True)
    assert 'change_machine_confirmed' in page and 'SEL-M2' in page
    fields={key:hidden(page,key) for key in ('access_csrf','version','revision')}
    old_checks=[(c.key,c.status,c.note) for c in sample.checks];old_data=copy.deepcopy(sample.data)
    assert client.post(prepare,data={**fields,'confirmed':'yes'}).status_code==400
    assert sample.machine_id==other.id and sample.state=='draft'
    no_csrf={**fields,'confirmed':'yes','change_machine_confirmed':'yes'};no_csrf.pop('access_csrf')
    assert client.post(prepare,data=no_csrf).status_code==400
    response=client.post(prepare,data={**fields,'confirmed':'yes','change_machine_confirmed':'yes'})
    assert response.status_code==303,response.get_data(as_text=True)
    assert sample.machine_id==m.id and sample.state=='in_progress' and sample.order.status=='in_arbeit'
    assert sample.snapshot['machine']['number']=='SEL-M1'
    assert TimeBooking.query.count()==n and sample.data==old_data and [(c.key,c.status,c.note) for c in sample.checks]==old_checks
    assert client.post(prepare,data={**fields,'confirmed':'yes','change_machine_confirmed':'yes'}).status_code==409
    assert command('setup',order_id=sample.order_id).status_code==303
    execute(m.id,user.id,'finish_setup',str(uuid4()),snapshot(m.id)['revision'])
    assert command('start',order_id=sample.order_id).status_code==303
    assert current_booking(m.id).process=='MUSTER'
    # A running sampling cannot be stolen by another machine despite confirmation.
    foreign=f'/production/machine/{other.id}/sampling/{sample.id}/prepare'
    page=client.get(foreign).get_data(as_text=True);fields={key:hidden(page,key) for key in ('access_csrf','version','revision')}
    assert client.post(foreign,data={**fields,'confirmed':'yes','change_machine_confirmed':'yes'}).status_code==409
    assert sample.machine_id==m.id and current_booking(m.id).process=='MUSTER'
    execute(m.id,user.id,'stop',str(uuid4()),snapshot(m.id)['revision'],comment='Musterlauf beendet')
    # Completed production still proposes the mounted tool; teardown needs no order.
    execute(m.id,user.id,'start',str(uuid4()),snapshot(m.id)['revision'],order_id=order.id)
    complete_order(order.id,user.id,str(uuid4()),completion_context(order)['revision'],good_qty='100',scrap_qty='0',confirmed=True)
    html=client.get(path).get_data(as_text=True);assert boot(html)['stock']['number']=='SEL-1'
    assert 'Werkzeug SEL-1 zum Abrüsten vorausfüllen' in html
    assert command('unsetup',order_id=order.id).status_code==303 # closed order explicitly ignored
    assert current_booking(m.id).tool_no=='SEL-1' and current_booking(m.id).order_id is None
    execute(m.id,user.id,'finish_setup',str(uuid4()),snapshot(m.id)['revision'])
    assert command('setup',tool='SEL-2').status_code==303 # manual, existing, order-free
    execute(m.id,user.id,'finish_setup',str(uuid4()),snapshot(m.id)['revision'])
    # Unique article assignment is a proposal, never an invented/master write.
    missing=Order(order_no='SEL-LEGACY',article=article.article_no,target_qty=1,cycle_time_s=30)
    assert tool_proposal(missing,{'SEL-1':ta})['number']=='SEL-1' and missing.tool_no is None
    # No-JS previews are read-only and prefill exact existing numbers.
    page=client.get(path).get_data(as_text=True)
    count=TimeBooking.query.count()
    preview=client.post(path,data=dict(access_csrf=hidden(page,'access_csrf'),action='preview_selection',order_id=sample.order_id))
    assert preview.status_code==200 and TimeBooking.query.count()==count
    # Queue bindings are NOT silently reassigned by sampling preparation.
    entry=ProductionPlanEntry(machine_id=other.id,order_id=unassigned.order_id,position=1,created_by_id=user.id,updated_by_id=user.id)
    db.session.add(entry);db.session.commit()
    html=client.get(path).get_data(as_text=True);info=boot(html)['orders'][str(unassigned.order_id)]
    assert 'Warteschlange auf SEL-M2' in info['note']
    page=client.get(info['prepare_url']).get_data(as_text=True);fields={key:hidden(page,key) for key in ('access_csrf','version','revision')}
    assert client.post(info['prepare_url'],data={**fields,'confirmed':'yes'}).status_code==409
    assert unassigned.machine_id is None and unassigned.state=='rework' and entry.machine_id==other.id
    # Production viewing is not permission to change sampling assignments.
    permission=Permission.query.filter_by(name='production.view').first()
    if not permission:permission=Permission(name='production.view');db.session.add(permission)
    reader=User(username='sel-reader',password_hash='unused',active=True,role=Role(name='sel-reader',active=True,permissions=[permission]));db.session.add(reader);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    assert denied.get(prepare).status_code==403
print('PASS: draft/rework/foreign sampling visible and labelled; explicit, versioned, audited preparation/transfer without bookings or QC changes; foreign running/queued bindings protected; concrete master proposals, exact tool checkbox, manual/stock/no-order teardown, no-JS previews, CSRF and separate permissions.')
