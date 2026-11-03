"""Target-cycle validation, isolated migration, forecast and form-layout regressions."""
import runpy
import sys
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
from html.parser import HTMLParser
from sqlalchemy import create_engine, text, inspect
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / "scripts/test_sampling_orders.py"))
app = fixture["app"]
from factoryos.extensions import db
from factoryos.modules.orders.models import Order
from factoryos.modules.orders.services.cycle_time import parse_cycle_time
from factoryos.modules.orders.services.erp_import_service import build_plan, default_choices
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.sampling.document_service import document_data
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.timeline_service import _forecast_for, get_machine_timeline
from factoryos.modules.production.services.calendar_service import get_or_create_calendar_settings
from scripts.upgrade_cycle_time import run_upgrade

engine = create_engine("sqlite://")
with engine.begin() as connection:
    connection.execute(text("CREATE TABLE orders (id INTEGER PRIMARY KEY, order_no TEXT, target_qty INTEGER, status TEXT)"))
    connection.execute(text("INSERT INTO orders VALUES (1, 'OLD', 100, 'open')"))
run_upgrade(True, engine); run_upgrade(False, engine); run_upgrade(False, engine)
assert "cycle_time_s" in {column["name"] for column in inspect(engine).get_columns("orders")}
with engine.connect() as connection:
    assert tuple(connection.execute(text("SELECT order_no,target_qty,status,cycle_time_s FROM orders")).one()) == ("OLD",100,"open",None)
engine.dispose()
for value in (None, "", "0", "-1", "NaN", "Infinity", "-Infinity", True):
    try: parse_cycle_time(value)
    except ValueError: pass
    else: raise AssertionError(value)
assert parse_cycle_time("12,5") == 12.5

class Controls(HTMLParser):
    def __init__(self): super().__init__(); self.fields=[]
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("input","select","textarea") and attrs.get("name"): self.fields.append(attrs)

with app.app_context():
    user = db.session.merge(fixture["user"])
    article = db.session.merge(fixture["article"])
    tool = db.session.merge(fixture["tool"])
    article.cycle_time_s = 12.5
    tool.cavities = 2
    article.tools = [tool]
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session: session["_user_id"]=str(user.id); session["_fresh"]=True
    html = client.get("/orders/create").get_data(as_text=True)
    controls = Controls(); controls.feed(html)
    assert "required" in next(field for field in controls.fields if field["name"]=="cycle_time_s")
    before = Order.query.count()
    with client.session_transaction() as session: access_token=session["access_csrf"]
    base = dict(order_no="CYCLE-ORDER", article=article.article_no, article_name="Cycle test",tool_no=tool.tool_no,target_qty="5",description="",location="",access_csrf=access_token)
    for value in ("","0","NaN","-1","Infinity"):
        response = client.post("/orders/create",data={**base,"cycle_time_s":value})
        assert response.status_code == 400
        assert Order.query.count() == before
    assert client.post("/orders/create",data={**base,"cycle_time_s":"23,5"}).status_code == 302
    order = Order.query.filter_by(order_no="CYCLE-ORDER").one()
    assert order.cycle_time_s == 23.5 and article.cycle_time_s == 12.5
    assert client.post(f"/orders/edit/{order.id}",data={**base,"target_qty":"999","cycle_time_s":"0"}).status_code == 400
    db.session.refresh(order)
    assert order.target_qty==5 and order.cycle_time_s==23.5
    assert client.post(f"/orders/edit/{order.id}",data={**base,"cycle_time_s":"30"}).status_code == 302
    assert order.cycle_time_s == 30 and order.status=="open"
    # Article forms: only placement changed, including the existing optional color settings.
    for path in ("/masterdata/articles/create", f"/masterdata/articles/edit/{article.id}"):
        page = client.get(path); assert page.status_code==200
        controls=Controls();controls.feed(page.get_data(as_text=True))
        names=[field["name"] for field in controls.fields]
        assert names.index("article_no") < names.index("tools") < names.index("material_id") < names.index("masterbatch_id") < names.index("masterbatch_percent")
        assert len([field for field in names if field=="tools"])==1
    # ERP must not bypass a mandatory target when the file/article has none.
    row = {"fields":{"order_no":"ERP-CYCLE","article_no":article.article_no,"quantity":"5","unit":"Stück","cycle_time_s":""},
           "choices":{},"source":[],"state":"pending","acknowledged":True}
    filled = default_choices(row, user)
    assert filled["fields"]["cycle_time_s"] == "12.5"
    filled["reviewed"] = True; filled["fields"]["cycle_time_s"]=""
    assert any("Soll-Zykluszeit" in error for error in build_plan(filled,user)["errors"])
    # Sampling has its own mandatory target, never an invented measured cycle.
    client.get("/orders/sampling/create")
    with client.session_transaction() as session: sampling_token=session["sampling_csrf"]
    data = dict(order_no="CYCLE-SAMPLE",reason="repair",target_qty="3",state="draft",
                csrf_token=sampling_token,article_id=str(article.id),tool_id=str(tool.id))
    assert client.post("/orders/sampling/create",data=data).status_code==400
    assert not Order.query.filter_by(order_no="CYCLE-SAMPLE").first()
    data["target_cycle_seconds"]="19.75"
    assert client.post("/orders/sampling/create",data=data).status_code==302
    sample = SamplingOrder.query.join(Order).filter(Order.order_no=="CYCLE-SAMPLE").one()
    assert sample.order.cycle_time_s==19.75 and sample.data["target_cycle_seconds"]==19.75
    assert sample.data["cycle_seconds"] is None
    doc = document_data(sample)
    assert ("Soll-Zykluszeit (Sekunden pro Maschinenzyklus)","19,75") in doc["groups"][0]["rows"]
    assert ("Ist-Zykluszeit (Sekunden)","-") in doc["groups"][2]["rows"]
    article.cycle_time_s=999;db.session.commit()
    assert sample.order.cycle_time_s==19.75 and order.cycle_time_s==30
    settings = get_or_create_calendar_settings()
    booking = SimpleNamespace(process="PROD",order=order,tool_no=tool.tool_no)
    def forecast(now, exceptions=(), tools=None):
        return _forecast_for(booking,{order.id:2},{article.article_no:article},now,settings,list(exceptions),
                             {tool.tool_no:tool} if tools is None else tools)
    result=forecast(datetime(2026,11,2,10))
    assert result["remaining_qty"]==3 and result["remaining_cycles"]==2 and result["remaining_seconds"]==60
    assert result["at"]==datetime(2026,11,2,10,1) and result["cycle_source"]=="Auftragssollwert"
    assert not result["cavities_assumed"]
    original_tools=list(article.tools)
    article.tools=[tool]
    saved_order_tool=order.tool_no
    order.tool_no=""
    booking.tool_no=""
    result=forecast(datetime(2026,11,2,10))
    assert not result["cavities_assumed"] and "Artikelstamm" in result["tool_source"]
    booking.tool_no=tool.tool_no
    order.tool_no=saved_order_tool
    article.tools=original_tools
    result=forecast(datetime(2026,11,2,10),tools={})
    assert result["cavities_assumed"] and result["remaining_seconds"]==90
    result=forecast(datetime(2026,11,7,5,59,30))
    assert result["at"]==datetime(2026,11,9,4,30,30)
    exceptions=[SimpleNamespace(start_at=datetime(2026,11,9),end_at=datetime(2026,11,10)),
                SimpleNamespace(start_at=datetime(2026,11,10),end_at=datetime(2026,11,11))]
    result=forecast(datetime(2026,11,7,5,59,30),exceptions)
    assert result["at"]==datetime(2026,11,11,0,0,30)
    order.cycle_time_s=None
    result=forecast(datetime(2026,11,2,10))
    assert "Altauftrag" in result["cycle_source"] and result["cycle_time_s"]==999
    db.session.rollback()
    timeline = get_machine_timeline(now=datetime(2026,11,2,10))
    assert timeline
print("PASS: required target in regular/sampling/ERP workflows, independent measured data, unchanged masters, legacy-preserving migration, article field order, rounded cavity-aware forecasts and weekly/holiday/bridge-day shutdown.")
