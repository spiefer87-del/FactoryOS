"""Machine detail navigation regression checks in an isolated SQLite database."""
import os
import secrets
import sys
import types
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from html.parser import HTMLParser

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
from factoryos.modules.masterdata.machines.models import Machine
from factoryos.modules.masterdata.machines.queries.machine_queries import get_machine_navigation, get_machines
from flask import g

with redirect_stdout(StringIO()):
    app = create_app()
app.config["TESTING"] = True

@app.before_request
def clear_test_user():
    g.pop("_login_user", None)
app.before_request_funcs[None].remove(clear_test_user)
app.before_request_funcs[None].insert(0, clear_test_user)

class NavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_nav = False
        self.links = {}
        self.disabled = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav" and attrs.get("aria-label") == "Zwischen Maschinen blättern":
            self.in_nav = True
        if not self.in_nav: return
        if tag == "a" and attrs.get("rel") in ("prev", "next"):
            self.links[attrs["rel"]] = attrs["href"]
        if tag == "button" and "disabled" in attrs: self.disabled += 1
    def handle_endtag(self, tag):
        if tag == "nav": self.in_nav = False

with app.app_context():
    db.create_all()
    view = Permission(name="machines.view")
    role = Role(name="production", active=True, permissions=[view])
    user = User(username="navigation-reader", password_hash="unused", active=True, role=role)
    denied_role = Role(name="none", active=True)
    denied = User(username="navigation-denied", password_hash="unused", active=True, role=denied_role)
    db.session.add_all([user, denied])
    # Deliberately insert in a different order, including an inactive machine.
    machines = [
        Machine(machine_no="M-030", machine_status="aktiv"),
        Machine(machine_no="M-010", machine_status="stillgelegt"),
        Machine(machine_no="M-020", machine_status="wartung", name="<test>"),
    ]
    db.session.add_all(machines)
    db.session.commit()
    ordered = get_machines()
    assert [m.machine_no for m in ordered] == ["M-010", "M-020", "M-030"]
    client = app.test_client()
    path = lambda machine: f"/masterdata/machines/{machine.id}"
    assert client.get(path(ordered[0])).status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(denied.id)
        session["_fresh"] = True
    assert client.get(path(ordered[0])).status_code == 403
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    for index, machine in enumerate(ordered):
        navigation = get_machine_navigation(machine)
        assert navigation["position"] == index + 1 and navigation["total"] == 3
        assert navigation["previous"] == (ordered[index - 1] if index else None)
        assert navigation["next"] == (ordered[index + 1] if index < 2 else None)
        response = client.get(path(machine))
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        parser = NavigationParser()
        parser.feed(html)
        assert f"Maschine {index + 1} von 3" in html
        assert parser.disabled == (1 if index in (0, 2) else 0)
        assert parser.links.get("prev") == (path(ordered[index - 1]) if index else None)
        assert parser.links.get("next") == (path(ordered[index + 1]) if index < 2 else None)
        assert "✏ Bearbeiten" not in html
        assert "Zur Übersicht" in html and "machine_navigation.css" in html
    assert "&lt;test&gt;" in client.get(path(ordered[1])).get_data(as_text=True)
    assert client.get("/masterdata/machines/999999").status_code == 404
    deleted_id = ordered[1].id
    db.session.delete(ordered[1])
    db.session.commit()
    assert get_machine_navigation(ordered[0])["next"] == ordered[2]
    assert client.get(f"/masterdata/machines/{deleted_id}").status_code == 404
    db.session.delete(ordered[2])
    db.session.commit()
    response = client.get(path(ordered[0]))
    parser = NavigationParser()
    parser.feed(response.get_data(as_text=True))
    assert parser.disabled == 2 and not parser.links
    assert "Maschine 1 von 1" in response.get_data(as_text=True)
print("PASS: sorted previous/next, first/last/single machine, deleted gaps, inactive machines, HTML escaping, view-only permission, denied/anonymous access and missing machines.")
