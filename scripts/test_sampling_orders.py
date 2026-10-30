"""Isolated workflow regression tests. Never opens the production database."""
import sys
import types
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules["cv2"] = types.ModuleType("cv2")  # unrelated drawing recognition
from factoryos.config import Config
Config.SQLALCHEMY_DATABASE_URI = "sqlite://"
Config.SESSION_COOKIE_SECURE = False
from factoryos import create_app
from factoryos.extensions import db
from flask import g
from factoryos.models.user import User
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.booking_service import start_production, end_booking
from factoryos.modules.sampling.models import SamplingOrder, SamplingCheck
from factoryos.modules.sampling.service import completion_errors
from factoryos.modules.sampling.definitions import CHECKS, REASONS
from scripts.upgrade_sampling_orders import run_upgrade

with redirect_stdout(StringIO()):
    app = create_app()
app.config.update(TESTING=True)

@app.before_request
def clear_test_user():
    g.pop("_login_user", None)

with app.app_context():
    db.create_all()
    user = User(username="test", password_hash="test", active=True)
    article = Article(article_no="A001", article_name="Deckel")
    tool = Tool(tool_no="W001", name="Werkzeug")
    material = Material(material_no="R001", name="ABS")
    customer = Customer(customer_no="K001", name="Kunde", active=True)
    machine = Machine(machine_no="M001", machine_status="aktiv")
    legacy = Order(order_no="LEGACY", status="offen", target_qty=100)
    db.session.add_all([user, article, tool, material, customer, machine, legacy])
    db.session.commit()
    # Test upgrade against pre-existing operational tables and preserve old orders.
    SamplingCheck.__table__.drop(bind=db.engine)
    SamplingOrder.__table__.drop(bind=db.engine)
    run_upgrade(True)
    run_upgrade()
    run_upgrade()
    assert Order.query.filter_by(order_no="LEGACY").count() == 1
    assert legacy.sampling is None
    client = app.test_client()
    assert client.get("/orders/sampling/").status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    assert client.get("/orders/sampling/create").status_code == 200
    with client.session_transaction() as session:
        token = session["sampling_csrf"]
    assert client.post("/orders/sampling/create", data={}).status_code == 400

    def form(number, reason):
        return dict(csrf_token=token, order_no=number, reason=reason,
                    material_confirmed="yes",
                    target_qty="10", state="review",
                    article_id=str(article.id), customer_id=str(customer.id),
                    tool_id=str(tool.id), material_id=str(material.id),
                    machine_id=str(machine.id), sampled_date=date.today().isoformat(),
                    operator="Prüfer", changes_result="Ergebnis erfüllt",
                    initial_scope="Maße und Funktion", initial_evidence="EMPB-001",
                    cavity_result="Nest 1 erfüllt", other_reason="Sonderversuch")

    def ready_checks(data, external="open"):
        for key in CHECKS:
            status = ("granted" if key == "internal" else external if key == "external" else "done")
            data["check_" + key] = status
            data["date_" + key] = date.today().isoformat() if status != "open" else ""
        return data

    data = ready_checks(form("M001", "repair"))
    assert client.post("/orders/sampling/create", data=data).status_code == 302
    repair = SamplingOrder.query.filter_by(reason="repair").one()
    assert repair.order.is_project is False
    assert not completion_errors(repair)
    assert client.get(f"/orders/sampling/{repair.id}").status_code == 200
    assert client.get(f"/orders/sampling/{repair.id}/edit").status_code == 200
    assert client.get("/orders/sampling/").status_code == 200
    assert client.get("/orders/overview").status_code == 200
    assert client.get(f"/orders/{repair.order_id}").location.endswith(f"/orders/sampling/{repair.id}")
    assert client.get(f"/orders/delete/{repair.order_id}").status_code == 302
    assert db.session.get(Order, repair.order_id)

    # Immutable reason and stale version guarded before changes are committed.
    data.update(version=str(repair.version), reason="color_change")
    assert client.post(f"/orders/sampling/{repair.id}/edit", data=data).status_code == 400
    assert repair.reason == "repair"
    data.update(reason="repair", version="0")
    assert client.post(f"/orders/sampling/{repair.id}/edit", data=data).status_code == 400

    # Booking is typed as sampling and completion blocked until booking stopped.
    with app.test_request_context():
        booking = start_production(user.id, repair.order_id, machine.id)
        assert booking.process == "MUSTER"
        assert any("Maschinenbuchung" in err for err in completion_errors(repair))
    assert client.post(f"/orders/sampling/{repair.id}/stop-booking",
                       data=dict(csrf_token=token)).status_code == 302
    assert not completion_errors(repair)
    completed = client.post(f"/orders/sampling/{repair.id}/complete",
                            data=dict(csrf_token=token, version=str(repair.version)))
    assert completed.status_code == 302
    assert repair.state == "completed" and repair.order.status == "fertig"
    assert client.get(f"/orders/sampling/{repair.id}/edit").status_code == 302
    response = client.post(f"/orders/sampling/{repair.id}/external", data=dict(
        csrf_token=token, version=str(repair.version), external_status="granted",
        external_date=date.today().isoformat(), external_note="Kundenfreigabe 1"))
    assert response.status_code == 302
    assert next(c for c in repair.checks if c.key == "external").status == "granted"

    # Initial cannot close with only internal approval.
    initial_data = ready_checks(form("M002", "initial"))
    assert client.post("/orders/sampling/create", data=initial_data).status_code == 302
    initial = SamplingOrder.query.filter_by(reason="initial").one()
    assert any("Externe" in err for err in completion_errors(initial))
    client.post(f"/orders/sampling/{initial.id}/complete",
                data=dict(csrf_token=token, version=str(initial.version)))
    assert initial.state != "completed"
    initial_data.update(version=str(initial.version))
    initial_data = ready_checks(initial_data, external="granted")
    assert client.post(f"/orders/sampling/{initial.id}/edit", data=initial_data).status_code == 302
    assert not completion_errors(initial)
    client.post(f"/orders/sampling/{initial.id}/complete",
                data=dict(csrf_token=token, version=str(initial.version)))
    assert initial.state == "completed"

    # Exactly one valid reason; all remaining distinct reasons supported.
    for reason in REASONS:
        if reason in ("repair", "initial"):
            continue
        data = form("TEST-" + reason, reason)
        assert client.post("/orders/sampling/create", data=data).status_code == 302
    data = form("BAD", "repair,color_change")
    assert client.post("/orders/sampling/create", data=data).status_code == 400
    data = form("M001", "repair")
    assert client.post("/orders/sampling/create", data=data).status_code == 400
    data = form("BAD-NUMBER", "repair")
    data["cycle_seconds"] = "NaN"
    assert client.post("/orders/sampling/create", data=data).status_code == 400
    assert Article.query.one().article_name == "Deckel"  # no master-data mutation
    # Snapshot survives later changes in the master data.
    article.article_name = "Neuer Stammdatenname"
    db.session.commit()
    assert repair.snapshot["article"]["name"] == "Deckel"
    # Used master data cannot be removed by ordinary delete routes.
    assert client.get(f"/masterdata/articles/delete/{article.id}").status_code == 302
    assert db.session.get(Article, article.id) is not None
    assert client.get(f"/masterdata/tools/delete/{tool.id}").status_code == 302
    assert db.session.get(Tool, tool.id) is not None
    assert client.post(f"/masterdata/customers/{customer.id}/delete").status_code == 302
    assert db.session.get(Customer, customer.id) is not None
print("PASS: upgrade twice, legacy preservation, forms, separate reasons, CSRF, completion gates, booking, snapshots, readonly completion, external follow-up, validation")
