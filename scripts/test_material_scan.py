"""Synthetic label OCR, conservative parser and read-only proposal flow."""
import runpy
import io
import re
import tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from PIL import Image,ImageDraw,ImageFont
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.materials.models import Material
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.masterdata.materials.services.material_scan_service import (
    parse_label,normalized_image,read_label,scan_slot,engine_info,ScanBusy,MAX_UPLOAD)

def values(result):return {p["field"]:p["value"] for p in result["proposals"]}
text="""Manufacturer: DEMO POLYMERS
Product: EXAMPLE ABS
Grade: G123
Material No.: 000123
ABS
Color: Natural
Color code: N001
RAL 9005
Delivery form: Granulate
Lot: BATCH-9988
Net weight: 25 kg"""
parsed=parse_label(text);proposal=values(parsed)
assert proposal["name"]=="EXAMPLE ABS G123" and proposal["polymer_type"]=="ABS"
assert proposal["manufacturer"]=="DEMO POLYMERS" and proposal["external_material_no"]=="000123"
assert proposal["material_type"]=="plastic" and proposal["ral_color"]=="RAL 9005"
assert proposal["delivery_form"]=="granulate"
assert not {"material_no","supplier_id","minimum_stock","hazardous_material","drying_temperature_c"}&set(proposal)
assert "BATCH" not in proposal["name"]
assert values(parse_label("Product: Test\nPC/ABS"))["polymer_type"]=="PC_ABS"
assert values(parse_label("Product: Test\nPA 6.6"))["polymer_type"]=="PA66"
assert "polymer_type" not in values(parse_label("Product: Test\nPA66 / PA6"))
assert "polymer_type" not in values(parse_label("Product: Test\nABS / PP"))
batch=values(parse_label("Product: BLUE 123\nMASTERBATCH\nCarrier PP\nColor: Blue"))
assert batch["material_type"]=="masterbatch" and "polymer_type" not in batch
assert "material_type" not in values(parse_label("Betriebsstoff und Hilfsstoff\nProduct: Test"))
assert not values(parse_label("Lot: 000123\nNet weight: 25 kg\nDate: 2026-11-03"))
assert values(parse_label("Hersteller\nDEMO GMBH\nHandelsname\nEXAMPLE 123\nABS"))["manufacturer"]=="DEMO GMBH"
assert values(parse_label("Product code: P123\nABS"))["external_material_no"]=="P123"
assert "name" not in values(parse_label("Product code: P123\nABS"))
assert values(parse_label("BASF\nProduct: TEST 123\nABS"))["manufacturer"]=="BASF"
assert next(p for p in parse_label("BASF\nProduct: TEST 123\nABS")["proposals"] if p["field"]=="manufacturer")["certainty"]=="review"
for raw in ("", "X"*20001):
    try:parse_label(raw)
    except ValueError:pass
    else:raise AssertionError("Invalid/oversized text accepted")
for raw in (b"",b"not an image",b"<svg></svg>",b"%PDF-1.4",b"x"*(MAX_UPLOAD+1)):
    try:normalized_image(raw)
    except ValueError:pass
    else:raise AssertionError("Invalid image accepted")

image=Image.new("RGB",(1500,1000),"white")
draw=ImageDraw.Draw(image);font=ImageFont.truetype("DejaVuSans.ttf",36)
for index,line in enumerate(text.splitlines()):draw.text((60,40+index*65),line,font=font,fill="black")
stream=io.BytesIO();image.save(stream,"JPEG",quality=95);photo=stream.getvalue()
normalized=normalized_image(photo)
assert normalized.mode=="L" and "exif" not in normalized.info

with app.app_context():
    app.config["MATERIAL_SCAN_TMP_DIR"]=str(ROOT.parent)
    admin=User.query.filter_by(username="test").one()
    existing=Material(material_no="SCAN-EXISTING",external_material_no="000123",name="EXAMPLE ABS G123",material_type="plastic",polymer_type="ABS")
    db.session.add(existing);db.session.commit()
    def client_for(user):
        c=app.test_client()
        with c.session_transaction() as session:session["_user_id"]=str(user.id);session["_fresh"]=True
        return c
    client=client_for(admin);page=client.get("/masterdata/materials/create")
    html=page.get_data(as_text=True)
    assert page.status_code==200 and 'capture="environment"' in html and 'id="material-create-form"' in html
    token=re.search(r'id="material-scan-csrf" value="([^"]+)"',html)[1]
    before=Material.query.count(),ChangeLog.query.count()
    path="/masterdata/materials/scan"
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={"access_csrf":token}).status_code==400
    assert client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(b"invalid"),"picture.jpg")}).status_code==400
    response=client.post(path+"/text",data={"access_csrf":token,"text":text})
    assert response.status_code==200 and response.json["duplicate_count"]==1
    assert response.json["duplicates"][0]["material_no"]==existing.material_no
    assert "no-store" in response.headers["Cache-Control"]
    with tempfile.TemporaryDirectory(prefix="scan-test-",dir=ROOT.parent) as directory:
        app.config["MATERIAL_SCAN_TMP_DIR"]=directory
        # Actual Tesseract run on a generated fixture, not a mocked recognition.
        engine_info()
        recognized,readability,languages=read_label(photo)
        assert "G123" in recognized and "ABS" in recognized and readability is not None
        assert list(Path(directory).iterdir())==[]
        response=client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(photo),"sack.jpg")})
        assert response.status_code==200,response.get_data(as_text=True)
        assert values(response.json)["polymer_type"]=="ABS"
        assert list(Path(directory).iterdir())==[]
        with patch("factoryos.modules.masterdata.materials.services.material_scan_service.subprocess.run",side_effect=__import__('subprocess').TimeoutExpired('tesseract',3)):
            assert client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(photo),"sack.jpg")}).status_code==503
        import subprocess
        original_run=subprocess.run
        def timeout_ocr(command,**kwargs):
            if "--list-langs" in command:return original_run(command,**kwargs)
            raise subprocess.TimeoutExpired("tesseract",10)
        with patch("factoryos.modules.masterdata.materials.services.material_scan_service.subprocess.run",side_effect=timeout_ocr):
            assert client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(photo),"sack.jpg")}).status_code==400
        assert list(Path(directory).iterdir())==[]
        with patch("factoryos.modules.masterdata.materials.routes.scan_routes.read_label",return_value=(text,35,"eng")):
            response=client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(photo),"sack.jpg")})
            assert all(p["certainty"]=="review" for p in response.json["proposals"])
    with scan_slot():
        assert client.post(path,data={"access_csrf":token,"photo":(io.BytesIO(photo),"sack.jpg")}).status_code==429
        try:
            with scan_slot():raise AssertionError("Concurrent OCR not blocked")
        except ScanBusy:pass
    assert before==(Material.query.count(),ChangeLog.query.count())
    # Extracting text or taking a photo NEVER inserts a material. Final manual submit does.
    payload=dict(access_csrf=token,material_no="SCAN-NEW",name="EXAMPLE ABS G123",material_type="plastic",polymer_type="ABS",manufacturer="DEMO POLYMERS",base_unit="kg",material_status="aktiv")
    assert client.post("/masterdata/materials/create",data={k:v for k,v in payload.items() if k!="access_csrf"}).status_code==400
    assert client.post("/masterdata/materials/create",data=payload).status_code==302
    assert Material.query.filter_by(material_no="SCAN-NEW").one().manufacturer=="DEMO POLYMERS"
    # A failed save keeps reviewed data and document inputs available.
    payload["material_no"]="SCAN-NEW"
    response=client.post("/masterdata/materials/create",data=payload)
    assert 'value="DEMO POLYMERS"' in response.get_data(as_text=True)
    assert 'name="data_sheets"' in response.get_data(as_text=True)
    view=Permission.query.filter_by(name="materials.view").first()
    if not view:view=Permission(name="materials.view");db.session.add(view)
    reader=User(username="scan-reader",password_hash="unused",active=True,role=Role(name="scan-reader",active=True,permissions=[view]))
    db.session.add(reader);db.session.commit();restricted=client_for(reader)
    assert restricted.post(path,data={"access_csrf":token}).status_code==403
    assert restricted.post(path+"/text",data={"access_csrf":token,"text":text}).status_code==403
    assert app.test_client().post(path).status_code==302
    assert not list(ROOT.parent.glob("factoryos-label-*"))
print("PASS: local real Tesseract OCR on synthetic label; bounded images/text, no persistent photos, conservative product/polymer/masterbatch parsing, no batch/weight confusion, duplicate hints, no writes until final submit, preserved reviewed fields, CSRF/permissions, timeout and OCR concurrency protection.")
