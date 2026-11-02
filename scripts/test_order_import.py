"""ERP parser and review/commit HTTP tests. Uses an isolated in-memory database only."""
import os
import secrets
import sys
import types
import re
from copy import deepcopy
from datetime import datetime
from io import BytesIO, StringIO
from pathlib import Path
from contextlib import redirect_stdout
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["FACTORYOS_SECRET_KEY"] = secrets.token_hex(48)
sys.modules["cv2"] = types.ModuleType("cv2")
from factoryos.config import Config
Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SESSION_COOKIE_SECURE = False
from factoryos import create_app
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.orders.models import Order
from factoryos.modules.orders.import_models import ERPImportBatch, ERPOrderData
from factoryos.modules.orders.services.erp_excel_reader import read_erp_excel, quantity
from factoryos.modules.orders.services.erp_import_service import build_plan, default_choices, options
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.production.models import TimeBooking
from scripts.upgrade_order_import import run_upgrade
from openpyxl import Workbook
from flask import g

HEADERS = ["FA-Nummer", "Artikelnummer", "Bezeichnung", "Fertigungsmenge", "Mengeneinheit",
           "Kundennummer", "Kundenkurzname", "Werkzeug", "Material", "Liefer-KW", "Status", "Auftragsart", "Zusatz"]
VALUES = [261742, "103010227", "Traverse_x000D_\nABS weiß", 2000, "Stück",
          10301, "Testkunde", "COR150 - Traverse Grohe", "00000004 - ABS weiß RAL 9003_x000D_\nPrüfzeugnis erforderlich", "44/26", 1, 0, "<script>BAD</script>"]

def excel(headers=HEADERS, rows=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "ERP"
    sheet.append(headers)
    for row in (rows if rows is not None else [VALUES]): sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream

sheet, parsed = read_erp_excel(excel())
assert sheet == "ERP" and len(parsed) == 1
source = parsed[0]
assert source["fields"]["order_no"] == "261742" and source["fields"]["tool_no"] == "COR150"
assert source["fields"]["material_no"] == "00000004"
assert source["fields"]["material_name"] == "ABS weiß RAL 9003"
assert any("Prüfzeugnis" in cell["value"] for cell in source["source"])
assert source["fields"]["article_name"] == "Traverse"
assert source["source"][-1]["value"] == "<script>BAD</script>"
for value in ("NaN", "Infinity", "0", "-1", "1,5", "2147483648", ""):
    try: quantity(value)
    except ValueError: pass
    else: raise AssertionError(value)
assert quantity("2.000") == 2000 and quantity("2000,0") == 2000
for headers, rows in [
    (["Not an order"], [["x"]]),
    (HEADERS + ["Auftragsnummer"], [VALUES + [123]]),
    (HEADERS, [[*VALUES[:3], "=1+1", *VALUES[4:]]]),
]:
    try: read_erp_excel(excel(headers, rows))
    except ValueError: pass
    else: raise AssertionError("invalid file accepted")

with redirect_stdout(StringIO()): app = create_app()
app.config["TESTING"] = True
@app.before_request
def clear_test_user(): g.pop("_login_user", None)
app.before_request_funcs[None].remove(clear_test_user)
app.before_request_funcs[None].insert(0, clear_test_user)

with app.app_context():
    db.create_all()
    admin = User(username="erp-admin", password_hash="unused", active=True, role=Role(name="admin", active=True))
    other = User(username="erp-other", password_hash="unused", active=True, role=Role(name="admin-other", active=True))
    viewer = User(username="erp-viewer", password_hash="unused", active=True, role=Role(name="viewer", active=True))
    db.session.add_all([admin, other, viewer])
    db.session.add(Order(order_no="LEGACY", article="old", target_qty=3, status="open"))
    db.session.commit()
    ERPImportBatch.__table__.drop(db.engine)
    ERPOrderData.__table__.drop(db.engine)
    run_upgrade(True); run_upgrade(); run_upgrade()
    assert Order.query.filter_by(order_no="LEGACY").one().target_qty == 3
    assert not other.role.permissions and not viewer.role.permissions
    other.role.permissions.append(Permission.query.filter_by(name="orders.excel_import").one())
    db.session.commit()
    def client_for(user):
        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id); session["_fresh"] = True
        return client
    client = client_for(admin)
    page = client.get("/orders/import")
    assert page.status_code == 200
    assert "/orders/import" in client.get("/orders/dashboard").get_data(as_text=True)
    token = re.search(r'name="access_csrf" value="([^"]+)"', page.get_data(as_text=True))[1]
    assert app.test_client().get("/orders/import").status_code == 302
    assert client_for(viewer).get("/orders/import").status_code == 403
    assert client.post("/orders/import", data={"file": (excel(), "erp.xlsx")}).status_code == 400
    def upload(rows=None):
        response = client.post("/orders/import", data={"access_csrf": token, "file": (excel(rows=rows), "erp.xlsx")})
        assert response.status_code == 302, response.get_data(as_text=True)
        return ERPImportBatch.query.filter_by(id=response.location.rsplit("/", 1)[-1]).one()
    def row_url(batch): return f"/orders/import/{batch.id}/row/0"
    def preview(batch, choices=None, fields=None, action="create"):
        row = default_choices(batch.rows[0], admin)
        data = {**row["fields"], "access_csrf":token, "version":str(batch.version), "intent":"preview",
                "acknowledged":"yes", "order_action":action, "machine_type":"injection_molding"}
        data.update({"choice_"+kind:choice for kind, choice in (choices or row["choices"]).items()})
        if fields: data.update(fields)
        response = client.post(row_url(batch), data=data)
        assert response.status_code == 302
        db.session.refresh(batch)
    def commit(batch):
        response = client.post(row_url(batch), data={"access_csrf":token,"version":str(batch.version),"intent":"commit"})
        db.session.refresh(batch)
        return response
    batch = upload()
    assert Order.query.count() == 1 and Article.query.count() == 0
    assert client_for(other).get(f"/orders/import/{batch.id}").status_code == 404
    assert client.get(row_url(batch)).status_code == 200
    choices = {"customer":"new","tool":"new","material":"new","article":"new","machine":"none"}
    preview(batch, choices)
    assert batch.rows[0]["state"] == "ready"
    html = client.get(row_url(batch)).get_data(as_text=True)
    assert "verbindlich übernehmen" in html and "&lt;script&gt;BAD&lt;/script&gt;" in html
    assert "<script>BAD</script>" not in html
    old_version = batch.version
    assert client.post(row_url(batch), data={"access_csrf":token,"version":str(old_version-1),"intent":"commit"}).status_code == 409
    assert commit(batch).status_code == 302
    assert batch.rows[0]["state"] == "imported"
    imported = Order.query.filter_by(order_no="261742").one()
    assert imported.article == "103010227" and imported.tool_no == "COR150" and imported.target_qty == 2000
    assert imported.status == "open" and TimeBooking.query.count() == 0
    assert [Customer.query.count(),Tool.query.count(),Material.query.count(),Article.query.count()] == [1,1,1,1]
    article = Article.query.one()
    assert article.customer_id == Customer.query.one().id and article.material_id == Material.query.one().id
    assert article.tools == [Tool.query.one()]
    assert imported.erp_import and len(imported.erp_import.snapshot["source"]) == len(HEADERS)
    assert client.get(f"/orders/{imported.id}").status_code == 200
    assert "Prüfzeugnis" in client.get(f"/orders/{imported.id}").get_data(as_text=True)
    # Same source again never duplicates or silently updates an order.
    repeat = upload()
    preview(repeat)
    assert repeat.rows[0]["state"] == "pending"
    # Explicit update, existing masters unchanged, prior ERP version retained.
    preview(repeat, fields={"quantity":"2500"}, action="update")
    assert repeat.rows[0]["state"] == "ready"
    assert commit(repeat).status_code == 302 and imported.target_qty == 2500
    assert len(imported.erp_import.snapshot["history"]) == 1
    # Master data changed after preview: stop before writes and require another review.
    second_values = list(VALUES); second_values[0] = 261743
    second = upload([second_values])
    preview(second)
    assert second.rows[0]["state"] == "ready"
    Customer.query.one().name = "Changed meanwhile"
    db.session.commit()
    assert commit(second).status_code == 302
    assert second.rows[0]["state"] == "pending" and Order.query.filter_by(order_no="261743").count() == 0
    # Unknown type/status remains a warning, invalid unit/quantity remains blocking.
    preview(second, fields={"quantity":"-2","unit":"kg"})
    assert second.rows[0]["state"] == "pending"
    preview(second, fields={"delivery_date":"2026-99-99"})
    assert second.rows[0]["state"] == "pending"
    # A new entity/order may not remain half-created on a failed transaction.
    atomic_values = list(VALUES)
    atomic_values[0] = 900000
    atomic_values[1] = "ATOMIC-ARTICLE"
    atomic_values[5] = "ATOMIC-CUSTOMER"
    atomic_values[7] = "ATOMIC-TOOL - New tool"
    atomic_values[8] = "ATOMIC-MATERIAL - New material"
    atomic = upload([atomic_values])
    preview(atomic, choices)
    assert atomic.rows[0]["state"] == "ready"
    import importlib
    from sqlalchemy.exc import IntegrityError
    routes = importlib.import_module("factoryos.modules.orders.routes.import_routes")
    original_commit = routes.commit_plan
    def interrupted(*args):
        original_commit(*args)
        raise IntegrityError("synthetic rollback check", {}, Exception("synthetic"))
    routes.commit_plan = interrupted
    try:
        assert commit(atomic).status_code == 302
    finally:
        routes.commit_plan = original_commit
    assert Order.query.filter_by(order_no="900000").count() == 0
    assert Customer.query.filter_by(customer_no="ATOMIC-CUSTOMER").count() == 0
    assert Tool.query.filter_by(tool_no="ATOMIC-TOOL").count() == 0
    assert Article.query.filter_by(article_no="ATOMIC-ARTICLE").count() == 0
    assert atomic.rows[0]["state"] == "ready"
    # Existing master data relationships are never rewritten to fit a different customer.
    alternative = Customer(customer_no="ALT", name="Alternative", active=True)
    db.session.add(alternative); db.session.commit()
    mismatch = default_choices(second.rows[0], admin)
    mismatch["choices"]["customer"] = "id:" + str(alternative.id)
    mismatch["acknowledged"] = True
    mismatch["fields"]["quantity"] = "2000"
    mismatch["fields"]["unit"] = "Stück"
    mismatch["fields"]["delivery_date"] = ""
    result = build_plan(mismatch, admin)
    assert any("Artikelstamm" in warning for warning in result["warnings"])
    assert article.customer_id != alternative.id
    # Duplicated FA positions need an explicit resolution.
    duplicate = upload([second_values, second_values])
    preview(duplicate)
    assert duplicate.rows[0]["state"] == "pending"
    assert "mehrfach" in client.get(row_url(duplicate)).get_data(as_text=True)
    # Missing creation rights block even manually forged choices.
    draft = default_choices(source, other)
    draft["choices"] = choices
    draft["acknowledged"] = True
    assert any("Berechtigung" in error for error in build_plan(draft, other)["errors"])
    assert all(not records for records in options(other).values())
    # Running/booked orders protected regardless of admin role.
    imported.status = "running"; db.session.commit()
    protected = upload(); preview(protected, action="update")
    assert protected.rows[0]["state"] == "pending"
    imported.status = "open"
    db.session.add(TimeBooking(order_id=imported.id,user_id=admin.id,type="STOP",start_time=datetime.utcnow(),end_time=datetime.utcnow()))
    db.session.commit()
    preview(protected, action="update")
    assert protected.rows[0]["state"] == "pending"
    # Escaping in the existing generic order overview was replaced by native autoescaping.
    db.session.add(Order(order_no="<script>ORDER</script>",article_name="<img src=x onerror=alert(1)>",target_qty=1))
    db.session.commit()
    html = client.get("/orders/overview").get_data(as_text=True)
    assert "<script>ORDER</script>" not in html and "&lt;script&gt;ORDER&lt;/script&gt;" in html
    assert "<img src=x" not in html

if len(sys.argv)>1:
    with open(sys.argv[1], "rb") as original:
        name, records = read_erp_excel(original)
    assert len(records)==1 and len(records[0]["source"])==36
    assert records[0]["fields"]["quantity"]=="2000"
    assert records[0]["fields"]["tool_no"]=="COR150"
    assert records[0]["fields"]["material_no"]=="00000004"
    print("PASS: provided ERP file read unchanged; all 36 source columns retained.")
print("PASS: parser, upgrade twice, no writes on upload, permissions/ownership/CSRF, explicit creates/updates, snapshots/history, exact references, stale preview/version rejection, duplicate FA rows, unit/quantity validation, running/booked protection and HTML escaping.")
