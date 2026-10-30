"""Read-only UI rendering checks in an isolated, disposable SQLite database."""
import sys
import types
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Optional drawing-recognition extension is unrelated to this rendering test.
sys.modules["cv2"] = types.ModuleType("cv2")
from factoryos.config import Config
Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SESSION_COOKIE_SECURE = False
from factoryos import create_app
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.machines.models import Machine
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.articles.models import Article

with redirect_stdout(StringIO()):
    app = create_app()
app.config.update(TESTING=True)

@app.before_request
def clear_test_identity():
    from flask import g
    g.pop("_login_user", None)

with app.app_context():
    db.create_all()
    role = Role(name="admin", active=True)
    role.permissions = [
        Permission(name=module + "." + action)
        for module in ("machines", "materials", "tools")
        for action in ("view", "create", "edit", "delete", "documents")
    ]
    user = User(username="ui-test", password_hash="unused", active=True, role=role)
    tool = Tool(tool_no="1009", name="Saugknopf-Neu", location="P079")
    machine = Machine(machine_no="M001", name="Spritzgießmaschine", machine_status="aktiv")
    material = Material(material_no="R001", name="ABS natur", material_type="plastic", polymer_type="ABS")
    customer = Customer(customer_no="0815", name="Test Kunde", contact="Herr Mustermann", city="Köln", active=True)
    article = Article(article_no="103010427", article_name="Deckel GH 2.0", customer=customer, material=material)
    db.session.add_all([user, tool, machine, material, customer, article])
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    paths = {
        "customers-detail": f"/masterdata/customers/{customer.id}",
        "customers-edit": f"/masterdata/customers/{customer.id}/edit",
        "customers-create": "/masterdata/customers/create",
        "tools-detail": f"/masterdata/tools/{tool.id}",
        "tools-edit": f"/masterdata/tools/edit/{tool.id}",
        "tools-create": "/masterdata/tools/create",
        "machines-detail": f"/masterdata/machines/{machine.id}",
        "machines-edit": f"/masterdata/machines/{machine.id}/edit",
        "machines-create": "/masterdata/machines/create",
        "materials-detail": f"/masterdata/materials/{material.id}",
        "materials-edit": f"/masterdata/materials/{material.id}/edit",
        "materials-create": "/masterdata/materials/create",
        "articles-detail": f"/masterdata/articles/{article.id}",
        "articles-edit": f"/masterdata/articles/edit/{article.id}",
        "articles-create": "/masterdata/articles/create",
    }
    # Optional generated local QA output, outside the repository.
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if output:
        output.mkdir(parents=True, exist_ok=True)
    for name, path in paths.items():
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
        html = response.get_data(as_text=True)
        assert "masterdata-theme" in html and "masterdata_theme.css" in html
        if name in ("tools-detail", "machines-detail", "materials-detail"):
            assert '<details class="md-activities">' in html
            assert '<details class="md-activities" open' not in html
        if output:
            import re
            # Self-contained rendered snapshots for browser checks, no external CDNs.
            html = re.sub(r'<script\b[^>]*>.*?</script>', "", html, flags=re.S)
            html = re.sub(r'<link\b[^>]*>', "", html)
            css = "\n".join((ROOT / "factoryos/static/css" / filename).read_text()
                            for filename in ("style.css", "qm_builder.css", "article_masterdata.css", "masterdata_theme.css"))
            html = html.replace("</head>", "<style>" + css + "</style></head>")
            (output / (name + ".html")).write_text(html)
    # Ensure the design is not loaded by production or orders.
    for path in ("/production/", "/orders/dashboard"):
        html = client.get(path).get_data(as_text=True)
        assert 'filename=\x27css/masterdata_theme.css' not in html
        assert 'href="/static/css/masterdata_theme.css"' not in html
print("PASS: 15 master-data views, collapsed activities and theme isolation.")
