"""Authoritative master-derived fields and modern overview, isolated DB only."""
import runpy
import re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.production.models import TimeBooking,ProductionPlanEntry
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.orders.services.order_form_service import parse_quantity

for value in (None,"","0","-1","1.5","1,5","NaN","Infinity","9999999999999999999999",True):
    try:parse_quantity(value)
    except ValueError:pass
    else:raise AssertionError(value)
assert parse_quantity("00020")==20

class Controls(HTMLParser):
    def __init__(self):super().__init__();self.fields=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("input","select","textarea"):self.fields.append(attrs)
        if tag=="a":self.links.append(attrs)

with app.app_context():
    admin=User.query.filter_by(username="test").one()
    one=Tool(tool_no="FORM-TOOL-1",name="Ein Werkzeug",cavities=2)
    two=Tool(tool_no="FORM-TOOL-2",name="Zweites Werkzeug")
    other=Tool(tool_no="FORM-UNRELATED",name="Nicht zugeordnet")
    article=Article(article_no="000FORM01",article_name="Name aus Stammdaten",cycle_time_s=12.5,tools=[one])
    multi=Article(article_no="FORM-MULTI",article_name="Mehrere Werkzeuge",tools=[one,two])
    empty=Article(article_no="FORM-EMPTY",article_name="Ohne Werkzeug")
    db.session.add_all([article,multi,empty,other]);db.session.commit()
    def client_for(user):
        client=app.test_client()
        with client.session_transaction() as session:session["_user_id"]=str(user.id);session["_fresh"]=True
        return client
    client=client_for(admin)
    page=client.get("/orders/create");assert page.status_code==200
    controls=Controls();controls.feed(page.get_data(as_text=True))
    fields={f.get("name"):f for f in controls.fields}
    assert "readonly" in fields["article_name"] and "required" in fields["target_qty"] and fields["target_qty"]["min"]=="1"
    assert "required" in fields["tool_no"] and "required" in fields["article"]
    assert "required" in fields["cycle_time_s"]
    with client.session_transaction() as session:token=session["access_csrf"]
    base=dict(access_csrf=token,order_no="FORM-ORDER",article=article.article_no,
        article_name="MANIPULIERTER NAME",target_qty="100",cycle_time_s="20",description="Notiz",location="Halle 1")
    before=Order.query.count()
    assert client.post("/orders/create",data={k:v for k,v in base.items() if k!="access_csrf"}).status_code==400
    for value in ("","0","-1","1.5","NaN","99999999999999999999999"):
        response=client.post("/orders/create",data={**base,"target_qty":value})
        assert response.status_code==400 and Order.query.count()==before
        assert "Stückzahl ist Pflicht" in response.get_data(as_text=True)
        assert "Halle 1" in response.get_data(as_text=True)
    assert client.post("/orders/create",data={**base,"article":"DOES-NOT-EXIST"}).status_code==400
    assert client.post("/orders/create",data={**base,"article":empty.article_no}).status_code==400
    assert client.post("/orders/create",data={**base,"article":multi.article_no}).status_code==400
    assert client.post("/orders/create",data={**base,"tool_no":other.tool_no}).status_code==400
    # The preview path works without JS and never creates an order/log.
    logs=ChangeLog.query.count()
    preview=client.post("/orders/create",data={**base,"intent":"preview","cycle_time_s":""})
    assert preview.status_code==200 and Order.query.count()==before and ChangeLog.query.count()==logs
    assert 'value="Name aus Stammdaten"' in preview.get_data(as_text=True)
    # Unique tool auto-derived on the server; posted name cannot override source.
    assert client.post("/orders/create",data=base).status_code==302
    order=Order.query.filter_by(order_no="FORM-ORDER").one()
    assert order.article_name==article.article_name and order.tool_no==one.tool_no and order.target_qty==100
    assert order.cycle_time_s==20 and article.cycle_time_s==12.5
    assert client.post("/orders/create",data=base).status_code==400
    # Multiple assignments require a valid deliberate choice.
    response=client.post("/orders/create",data={**base,"order_no":"FORM-SECOND","article":multi.article_no,"tool_no":two.tool_no})
    assert response.status_code==302
    second=Order.query.filter_by(order_no="FORM-SECOND").one()
    assert second.tool_no==two.tool_no and second.article_name==multi.article_name
    # Editing refreshes from master, never from a forged readonly field.
    article.article_name="Umbenannter Stammdatensatz";db.session.commit()
    payload={**base,"article_name":"WIEDER MANIPULIERT","tool_no":one.tool_no,"target_qty":"120"}
    assert client.post(f"/orders/edit/{order.id}",data=payload).status_code==302
    assert order.article_name==article.article_name and order.target_qty==120
    # Running/planned work cannot change article/tool binding or become finished.
    plan=ProductionPlanEntry(machine_id=Machine.query.filter_by(machine_no="M001").one().id,order_id=second.id,position=1,state="queued",created_by_id=admin.id,updated_by_id=admin.id)
    db.session.add(plan);db.session.commit()
    old=second.tool_no
    assert client.post(f"/orders/edit/{second.id}",data={**base,"article":multi.article_no,"tool_no":one.tool_no}).status_code==400
    db.session.refresh(second);assert second.tool_no==old
    assert client.post(f"/orders/edit/{second.id}",data={**base,"article":multi.article_no,"tool_no":two.tool_no,"status":"fertig"}).status_code==400
    # An explicit legacy/ERP binding can be retained, not silently replaced.
    legacy=Order(order_no="FORM-LEGACY",article=article.article_no,article_name="",tool_no=other.tool_no,target_qty=10,cycle_time_s=10)
    unknown=Order(order_no="FORM-UNKNOWN",article="ARTICLE-DOES-NOT-EXIST",article_name="Historischer Name",target_qty=None)
    proposed=Order(order_no="FORM-PROPOSAL",article=article.article_no,article_name="",target_qty=10,cycle_time_s=10)
    project=Order(order_no="FORM-PROJECT",article="Projekttext",article_name="Projektname",tool_no=other.tool_no,target_qty=0,is_project=True)
    db.session.add_all([legacy,unknown,proposed,project]);db.session.commit()
    assert client.post(f"/orders/edit/{legacy.id}",data={**base,"tool_no":other.tool_no}).status_code==302
    assert legacy.tool_no==other.tool_no
    assert client.post(f"/orders/edit/{project.id}",data={"access_csrf":token,"description":"Projekt bleibt bestehen","status":project.status,"article":"FALSCH","article_name":"FALSCH","target_qty":"999"}).status_code==302
    assert project.article=="Projekttext" and project.article_name=="Projektname" and project.target_qty==0
    # Overview/master links and legacy display suggestions are read-only.
    names_before={o.id:o.article_name for o in Order.query.all()};before_count=ChangeLog.query.count()
    html=client.get("/orders/overview").get_data(as_text=True)
    assert "Werkzeug" in html and "Stückzahl" in html and "Aufträge insgesamt" in html
    assert f'href="/masterdata/articles/{article.id}"' in html
    assert "orders-table-scroll" in html and "Seitlich".lower() in html.lower()
    assert "Artikelvorschlag" in html and "noch nicht am Auftrag gespeichert" in html
    assert "Historischer Name" in html and "Kein zugeordneter Artikelstamm" in html
    assert names_before=={o.id:o.article_name for o in Order.query.all()} and ChangeLog.query.count()==before_count
    assert proposed.tool_no is None and proposed.article_name==""
    # Escaping and action visibility for a read-only role.
    article.article_name='<script>NAME</script>';db.session.commit()
    html=client.get("/orders/overview").get_data(as_text=True)
    assert "<script>NAME</script>" not in html and "&lt;script&gt;NAME&lt;/script&gt;" in html
    view=Permission.query.filter_by(name="orders.view").first()
    if not view:view=Permission(name="orders.view");db.session.add(view)
    reader=User(username="order-form-reader",password_hash="unused",active=True,role=Role(name="order-form-reader",active=True,permissions=[view]))
    db.session.add(reader);db.session.commit();restricted=client_for(reader)
    html=restricted.get("/orders/overview").get_data(as_text=True)
    assert "Neuer Auftrag" not in html and "Bearbeiten" not in html and "Löschen" not in html
    assert f'href="/masterdata/articles/{article.id}"' not in html
    assert restricted.get("/orders/create").status_code==403 and restricted.post("/orders/create",data=base).status_code==403
    assert app.test_client().get("/orders/create").status_code==302
print("PASS: readonly/server-authoritative article name, mandatory positive integer quantity and mapped tool, deliberate multi-tool choice, forged fields rejected/ignored, CSRF, no-JS preview, preserved values/ERP tools/project workflow, planned binding protection, modern linked overview, legacy suggestions without writes and permissions/escaping.")
