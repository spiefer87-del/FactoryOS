"""Quantity correction navigation, existing ACL and 10000 -> 15000 recalculation."""
import runpy,re
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

fixture=runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import TimeBooking,QuantityReport,ProductionPlanEntry
from factoryos.modules.production_deviations.models import ProductionDeviationConfirmation
from factoryos.modules.production.services.order_statistics import order_statistics
from factoryos.modules.production.services.timeline_service import get_machine_timeline
from factoryos.modules.production.services.planning_service import build_schedule
from factoryos.core.models.change_log import ChangeLog

with app.app_context():
    admin=db.session.merge(fixture['user'])
    def permission(name):return Permission.query.filter_by(name=name).first() or Permission(name=name)
    rights=[permission(name) for name in ('production.view','orders.view','production.confirm_deviation')]
    reader=User(username='quantity-reader',password_hash='unused',active=True,role=Role(name='quantity-reader',active=True,permissions=rights))
    editor=User(username='quantity-editor',password_hash='unused',active=True,role=Role(name='quantity-editor',active=True,permissions=[*rights,permission('orders.edit')]))
    tool=Tool(tool_no='QUANTITY-NAV',name='Tool',cavities=8)
    article=Article(article_no='QUANTITY-NAV',article_name='Testartikel',tools=[tool],cycle_time_s=30.92)
    machine=Machine(machine_no='QUANTITY-NAV',machine_status='aktiv')
    order=Order(order_no='QUANTITY-NAV',status='running',target_qty=10000,cycle_time_s=30.92,article=article.article_no,tool_no=tool.tool_no)
    successor=Order(order_no='QUANTITY-NEXT',status='open',target_qty=2000,cycle_time_s=30.92,article=article.article_no,tool_no=tool.tool_no)
    db.session.add_all([reader,editor,tool,article,machine,order,successor]);db.session.flush()
    now=datetime(2026,11,18,12)
    booking=TimeBooking(user_id=admin.id,order_id=order.id,machine_id=machine.id,tool_no=tool.tool_no,
        type='START',process='PROD',start_time=now-timedelta(hours=13,minutes=3))
    entry=ProductionPlanEntry(machine_id=machine.id,order_id=successor.id,position=1,state='queued',setup_minutes=10,created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add_all([booking,entry]);db.session.commit()
    def client_for(person):
        c=app.test_client()
        with c.session_transaction() as s:s['_user_id']=str(person.id);s['_fresh']=True
        return c
    readonly=client_for(reader);writable=client_for(editor)
    original=order_statistics(order,now)
    assert original['deviation']['kind']=='overdue' and original['eta'] is None
    reason=ProductionDeviationConfirmation(order_id=order.id,user_id=admin.id,kind='overdue',
        signature=original['deviation']['signature'],category='Sonstiger Grund',
        reason='Ursprüngliche Zeitbasis zur Prüfung dokumentiert',snapshot=original['deviation']['snapshot'])
    db.session.add(reason);db.session.commit()
    unchanged=[(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()]
    count=QuantityReport.query.count();confirmations=ProductionDeviationConfirmation.query.count()
    path=f'/production/deviations/order/{order.id}';edit_path=f'/orders/edit/{order.id}'
    with patch('factoryos.modules.production.routes.dashboard_routes.get_machine_timeline',side_effect=lambda *a,**kw:get_machine_timeline('24h',now)):
        html=readonly.get('/production/booking').get_data(as_text=True)
        assert f'data-quantity-hint-order="{order.id}"' in html and 'Auftragsmenge noch aktuell?' in html
        assert edit_path not in html
        response=writable.get('/production/booking');assert response.status_code==200
        html=response.get_data(as_text=True)
        assert edit_path+'?focus=quantity#order-quantity-section' in html
        assert 'timeline-order-edit' in html and 'begründet' in html
    assert readonly.get(edit_path).status_code==403
    assert readonly.post(edit_path,data={'target_qty':'15000'}).status_code==403
    with patch('factoryos.modules.production_deviations.routes.order_statistics',side_effect=lambda obj:order_statistics(obj,now)):
        response=readonly.get(path);assert response.status_code==200
        assert 'Stückzahl korrigieren' not in response.get_data(as_text=True)
        with readonly.session_transaction() as s:token=s['access_csrf']
        assert readonly.post(path,data={'access_csrf':token,'category':'correct_quantity'}).status_code==403
        assert writable.post(path,data={'category':'correct_quantity'}).status_code==400
        html=writable.get(path).get_data(as_text=True)
        first_option=re.search(r'<select id="deviation-reason".*?<option value="">.*?</option>\s*<option value="([^"]+)"',html,re.S)[1]
        assert first_option=='correct_quantity' and 'data-order-edit-url=' in html
        with writable.session_transaction() as s:token=s['access_csrf']
        response=writable.post(path,data={'access_csrf':token,'category':'correct_quantity'})
        assert response.status_code==303
        target=urlsplit(response.headers['Location'])
        assert target.path==edit_path and target.query=='focus=quantity' and target.fragment=='order-quantity-section'
    assert order.target_qty==10000 and QuantityReport.query.count()==count
    assert ProductionDeviationConfirmation.query.count()==confirmations
    response=writable.get(target.path+'?'+target.query)
    html=response.get_data(as_text=True)
    field=re.search(r'<input id="order-target-qty"[^>]+>',html)[0]
    assert 'value="10000"' in field and 'autofocus' in field
    assert 'neue gesamte Fertigungsmenge' in html
    data=dict(access_csrf=token,intent='save',article=article.article_no,tool_no=tool.tool_no,
              cycle_time_s='30.92',target_qty='15000',status='running',description='',location='')
    assert writable.post(edit_path,data={**data,'access_csrf':'bad'}).status_code==400
    assert writable.post(edit_path,data=data).status_code==302
    db.session.refresh(order)
    assert order.target_qty==15000 and order.cycle_time_s==30.92 and order.status=='running'
    updated=order_statistics(order,now)
    assert updated['deviation']['kind'] is None and updated['eta']>now
    assert abs(updated['forecast']['remaining_seconds']-10995)<0.01
    plan=next(l for l in build_schedule(now)['machines'] if l['machine'].id==machine.id)
    assert plan['rows'][0]['setup_start']==updated['eta'] and plan['rows'][0]['start']>updated['eta']
    with patch('factoryos.modules.production.routes.dashboard_routes.get_machine_timeline',side_effect=lambda *a,**kw:get_machine_timeline('24h',now)):
        html=writable.get('/production/booking').get_data(as_text=True)
        assert f'data-quantity-hint-order="{order.id}"' not in html
    assert QuantityReport.query.count()==count and [(b.id,b.start_time,b.end_time) for b in TimeBooking.query.all()]==unchanged
    assert ProductionDeviationConfirmation.query.count()==confirmations
    assert updated['deviation']['history'][0].id==reason.id
    log=ChangeLog.query.filter_by(entity_type='order',entity_id=order.id,category='orders').order_by(ChangeLog.id.desc()).first()
    assert log.user_id==editor.id and log.changes['target_qty']=={'old':10000,'new':15000}
    # A real overrun remains when the adjusted budget is still exhausted.
    order.target_qty=10001;db.session.commit()
    with patch('factoryos.modules.production.routes.dashboard_routes.get_machine_timeline',side_effect=lambda *a,**kw:get_machine_timeline('24h',now)):
        assert f'data-quantity-hint-order="{order.id}"' in writable.get('/production/booking').get_data(as_text=True)
    # Closed/locked orders cannot be opened through the correction action.
    order.status='finished';db.session.commit()
    with patch('factoryos.modules.production_deviations.routes.order_statistics',side_effect=lambda obj:order_statistics(obj,now)):
        assert 'Stückzahl korrigieren' not in writable.get(path).get_data(as_text=True)
        assert writable.post(path,data={'access_csrf':token,'category':'correct_quantity'}).status_code==403

print('PASS: actionable timeline hints, top reason action, navigation-only redirect and focused quantity field, read/edit permissions and forged POST/CSRF guards, existing 10000->15000 save/audit, refreshed ETA and successor planning, no quantity/booking/confirmation fabrication, retained history and genuine overruns')
