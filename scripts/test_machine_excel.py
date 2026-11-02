"""Isolated SQLite regression tests; never opens the production database."""
import os
import sys
import types
import secrets
from pathlib import Path
from io import BytesIO
from contextlib import redirect_stdout
from io import StringIO
from datetime import datetime
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
from factoryos.modules.masterdata.machines.models import Machine, InjectionMoldingData
from factoryos.modules.masterdata.machines.services.machine_excel_schema import KEYS, HEADERS, machine_workbook
from factoryos.modules.masterdata.machines.services.machine_export_service import export_machines_to_excel
from factoryos.modules.masterdata.machines.services.machine_import_service import import_machines_from_excel
from openpyxl import Workbook, load_workbook

def file(headers, rows, title="Maschinen"):
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(headers)
    for row in rows: ws.append(row)
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream

with redirect_stdout(StringIO()):
    app = create_app()
app.config["TESTING"] = True
from flask import g
@app.before_request
def clear_test_user():
    g.pop("_login_user", None)
app.before_request_funcs[None].remove(clear_test_user)
app.before_request_funcs[None].insert(0, clear_test_user)
with app.test_request_context():
    db.create_all()
    admin = Role(name="admin", active=True)
    user = User(username="excel-test", password_hash="unused", active=True, role=admin)
    db.session.add(user)
    db.session.flush()
    machine = Machine(machine_no="00123", created_by_id=user.id, machine_type="injection_molding",
                      machine_status="wartung", name="=Literal text", external_machine_no="0005",
                      serial_no="000009", build_year=2020, operating_hours=0,
                      last_service_at=datetime(2026, 11, 2, 14, 32, 17),
                      next_service_at=datetime(2027, 1, 1, 8, 10, 11))
    machine.injection_molding_data = InjectionMoldingData(**{
        key: (0 if key == "heating_zones" else index + 0.25)
        for index, key in enumerate(KEYS[16:])})
    other = Machine(machine_no="F01", machine_type="milling", machine_status="stillgelegt")
    db.session.add_all([machine, other])
    db.session.commit()
    def snapshot(machine):
        return [getattr(machine if i < 16 else machine.injection_molding_data, key, None)
                for i, key in enumerate(KEYS)]
    before = snapshot(machine)
    stream = export_machines_to_excel()
    wb = load_workbook(stream)
    assert wb.sheetnames == ["Maschinen", "Hinweise"]
    assert [c.value for c in wb["Maschinen"][1]] == HEADERS
    assert wb["Maschinen"]["C2"].data_type == "s"
    assert wb["Maschinen"]["A2"].value == "00123"
    template = load_workbook(machine_workbook())
    assert [c.value for c in template.active[1]] == HEADERS
    assert template.active.max_row == 1
    stream.seek(0)
    result = import_machines_from_excel(stream, user.id)
    assert result == {"created": 0, "updated": 2, "errors": []}, result
    db.session.expire_all()
    assert snapshot(machine) == before, (before, snapshot(machine))
    assert other.machine_type == "milling" and other.injection_molding_data is None
    # Legacy readable export, ignored audit/internal columns, full date/time.
    result = import_machines_from_excel(file(
        ["Maschinennummer", "Maschinentyp", "Maschinentyp intern", "Status", "Status intern", "Erstellt am", "Letzte Wartung"],
        [["00123", "Spritzgießmaschine", "injection_molding", "Wartung", "wartung", "ignored", "02.11.2026 14:32:17"]]), user.id)
    assert not result["errors"], result
    assert snapshot(machine) == before
    # Old technical template, normalized German headers, partial updates.
    result = import_machines_from_excel(file(["machine_no", "name"], [["00123", "Updated"]]), user.id)
    assert not result["errors"] and machine.machine_status == "wartung", result
    assert machine.injection_molding_data.clamping_force_kn == before[16]
    result = import_machines_from_excel(file(["\ufeff Maschinennummer ", "Betriebsstunden"], [["NEU", 0]]), user.id)
    assert result["created"] == 1 and not result["errors"]
    assert Machine.query.filter_by(machine_no="NEU").one().operating_hours == 0
    result = import_machines_from_excel(file(["machine_no", "clamping_force_kn"], [["NEU", "12,75"]], title="Importformat"), user.id)
    assert not result["errors"] and Machine.query.filter_by(machine_no="NEU").one().injection_molding_data.clamping_force_kn == 12.75
    result = import_machines_from_excel(file(["machine_no", "machine_status"], [["00123", "unbekannt"]]), user.id)
    assert len(result["errors"]) == 1 and machine.machine_status == "wartung"
    result = import_machines_from_excel(file(["machine_no", "name", "build_year"], [["00123", "must not save", 2020.5]]), user.id)
    assert len(result["errors"]) == 1 and machine.name == "Updated"
    result = import_machines_from_excel(file(["machine_no", "name"], [["00123", None]]), user.id)
    assert machine.name is None and not result["errors"]
    result = import_machines_from_excel(file(["machine_no", "build_year"], [["BAD", 2020.5], ["GOOD", 2020]]), user.id)
    assert len(result["errors"]) == 1 and result["created"] == 1
    assert Machine.query.filter_by(machine_no="BAD").count() == 0
    for value in ("NaN", "inf", -1):
        result = import_machines_from_excel(file(["machine_no", "operating_hours"], [["INVALID", value]]), user.id)
        assert len(result["errors"]) == 1 and Machine.query.filter_by(machine_no="INVALID").count() == 0
    result = import_machines_from_excel(file(["machine_no", "name"], [["DUP", "a"], ["DUP", "b"]]), user.id)
    assert len(result["errors"]) == 2 and Machine.query.filter_by(machine_no="DUP").count() == 0
    for headers, rows in [
        (["other"], [["x"]]),
        (["machine_no", "Maschinennummer"], [["x", "x"]]),
        (["machine_no", "name"], [["FORMULA", "=1+1"]]),
    ]:
        try: import_machines_from_excel(file(headers, rows), user.id)
        except ValueError: pass
        else: raise AssertionError("Invalid workbook was accepted")
    assert Machine.query.filter_by(machine_no="FORMULA").count() == 0
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    response = client.get("/masterdata/machines/import/template")
    assert response.status_code == 200
    assert [c.value for c in load_workbook(BytesIO(response.data)).active[1]] == HEADERS
    response = client.get("/masterdata/machines/export/excel")
    assert response.status_code == 200
    assert [c.value for c in load_workbook(BytesIO(response.data)).active[1]] == HEADERS
print("PASS: machine export/import roundtrip, all technical fields, dates/times, blank template, old headers, partial updates, zero/leading zeros, literal text, invalid rows, duplicate/formula rejection, download routes.")
