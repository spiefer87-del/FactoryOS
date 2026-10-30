"""Isolated integration checks, never opens the operational database."""
import sys
import types
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Unrelated drawing recognition is not exercised by these tests.
sys.modules["cv2"] = types.ModuleType("cv2")

from factoryos.config import Config
Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SESSION_COOKIE_SECURE = False
from factoryos import create_app
from factoryos.extensions import db
from sqlalchemy import text, inspect
from factoryos.models.user import User
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.tools.models import Tool
from werkzeug.datastructures import MultiDict
from factoryos.modules.masterdata.articles.services.article_service import create_article, update_article
from scripts.upgrade_customer_masterdata import run_upgrade

with redirect_stdout(StringIO()):
    app = create_app()
app.config.update(TESTING=True)
@app.before_request
def reset_test_login_cache():
    from flask import g
    g.pop("_login_user", None)

with app.app_context():
    # Simulate an old database without the new customer column.
    with db.engine.begin() as conn:
        conn.execute(text("CREATE TABLE articles (id INTEGER PRIMARY KEY, article_no VARCHAR(50), article_name VARCHAR(200))"))
        conn.execute(text("INSERT INTO articles VALUES (1, 'OLD', 'Bestandsartikel')"))
    run_upgrade(check_only=True)
    assert "customer_id" not in {c["name"] for c in inspect(db.engine).get_columns("articles")}
    run_upgrade()
    run_upgrade()
    with db.engine.connect() as conn:
        assert conn.execute(text("SELECT article_no, customer_id FROM articles")).one() == ("OLD", None)
    # Rebuild only the disposable in-memory test database for application flows.
    db.drop_all()
    db.create_all()
    user = User(username="test", password_hash="not-used", active=True)
    db.session.add(user)
    db.session.commit()
    client = app.test_client()
    assert client.get("/masterdata/customers/").status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    assert client.post("/masterdata/customers/create", data={"customer_no":"K001","name":"Testkunde","active":"yes"}).status_code == 302
    customer = Customer.query.one()
    assert client.post("/masterdata/customers/create", data={"customer_no":"K001","name":"Duplikat"}).status_code == 400
    for path in ["/masterdata/customers/", f"/masterdata/customers/{customer.id}", f"/masterdata/customers/{customer.id}/edit", "/masterdata/articles/create"]:
        assert client.get(path).status_code == 200, path
    with app.test_request_context():
        tool = Tool(tool_no="W001", name="Test")
        db.session.add(tool)
        db.session.commit()
        form = MultiDict({"article_no":"A001","article_name":"Test","status":"active","tools":str(tool.id)})
        article = create_article(form)
        assert article.customer_id is None
        assert tool in article.tools
        form["customer_id"] = str(customer.id)
        update_article(article, form)
        assert article.customer_id == customer.id
    assert client.post(f"/masterdata/customers/{customer.id}/delete").status_code == 302
    assert db.session.get(Customer, customer.id) is not None
    for path in ["/masterdata/articles/list", f"/masterdata/articles/{article.id}", f"/masterdata/articles/edit/{article.id}"]:
        assert client.get(path).status_code == 200, path
    with app.test_request_context():
        form["customer_id"] = ""
        update_article(article, form)
        assert article.customer_id is None
        form["customer_id"] = "999999"
        try:
            update_article(article, form)
        except ValueError:
            db.session.rollback()
        else:
            raise AssertionError("Unknown customer accepted")
    assert client.post(f"/masterdata/customers/{customer.id}/delete").status_code == 302
    assert Customer.query.count() == 0
print("PASS: legacy upgrade twice, data preservation, authentication, CRUD, duplicate number, optional link/unlink, delete protection, tools, pages")
