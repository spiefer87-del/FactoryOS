"""Compact warehouse UI; existing transactional service remains unchanged."""
import runpy
from pathlib import Path
from html.parser import HTMLParser
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_inventory.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.inventory.models import WarehouseEvent
from factoryos.modules.inventory.service import LABELS

class Parser(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.tiles=[];self.tables=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a':
            self.links.append(attrs.get('href',''))
            if 'dashboard-card' in attrs.get('class','').split():self.tiles.append(attrs.get('href'))
        if tag=='table':self.tables.append(attrs.get('id'))

with app.app_context():
    user=db.session.merge(fixture['user']);client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    count=WarehouseEvent.query.count()
    def page(view):
        response=client.get('/warehouse/?view='+view);assert response.status_code==200
        html=response.get_data(as_text=True);parser=Parser();parser.feed(html);return html,parser
    html,home=page('overview')
    assert len(home.tiles)==4
    assert set(home.tiles)=={'/warehouse/?view=incoming','/warehouse/?view=stock','/warehouse/?view=outbound','/warehouse/?view=manage'}
    assert home.tables==['warehouse-stock']
    assert 'warehouse-actions' not in html and '<nav>' not in html
    assert all('/warehouse/'+action not in home.links for action in LABELS)
    groups={'incoming':{'transfer','receive','reject','cancel'},'stock':{'move','release','reserve','block','scrap','opening'},'outbound':{'pick','ship','unreserve','return'},'locations':{'location'},'journal':{'reverse'}}
    seen=set()
    for view,actions in groups.items():
        html,parsed=page(view)
        actual={a for a in LABELS if '/warehouse/'+a in parsed.links};assert actual==actions,(view,actual)
        seen.update(actual)
        assert '/warehouse/?view=overview' in parsed.links
        for action in actions:
            response=client.get('/warehouse/'+action);assert response.status_code==200
            assert 'view='+view in response.get_data(as_text=True)
    assert seen==set(LABELS)
    _,manage=page('manage');assert len(manage.tiles)==2
    assert WarehouseEvent.query.count()==count
    # View-only user cannot see booking links, including hidden advanced actions.
    reader=db.session.merge(fixture['reader']);limited=app.test_client()
    with limited.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    for view in groups:
        response=limited.get('/warehouse/?view='+view);assert response.status_code==200
        parsed=Parser();parsed.feed(response.get_data(as_text=True))
        assert all('/warehouse/'+a not in parsed.links for a in LABELS)
print('PASS: four home tiles, one stock overview, no top button wall, grouped actions complete, two management tiles, contextual back links, read-only GET and permission filtering.')
