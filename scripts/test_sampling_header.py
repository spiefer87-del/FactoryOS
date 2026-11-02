"""Read-only header/layout regression against disposable synthetic records."""
import runpy
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / "scripts/test_sampling_orders.py"))
app = fixture["app"]
from flask import render_template
from factoryos.extensions import db
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.sampling.document_service import document_data
from factoryos.modules.sampling.pdf_service import build_pdf
from factoryos.modules.masterdata.shared.constants import MATERIAL_TYPES

with app.app_context():
    record = SamplingOrder.query.filter_by(reason="repair").one()
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(fixture["user"].id)
        session["_fresh"] = True
    version_before = record.version
    data_before, snapshot_before = dict(record.data), dict(record.snapshot)
    form = client.get("/orders/sampling/create").get_data(as_text=True)
    assert form.index('id="reason"') < form.index('id="order_no"')
    assert form.count('name="other_reason"') == 1
    assert 'sampling-key-field' in form
    assert 'id="tool_id"' in form and 'id="article_id"' in form
    page = client.get(f"/orders/sampling/{record.id}").get_data(as_text=True)
    assert 'id="sampling-detail-purpose"' in page
    assert page.index('id="sampling-detail-purpose"') < page.index('Weitere Auftragsdaten')
    assert record.snapshot["tool"]["number"] in page
    document = document_data(record)
    assert document["key_facts"][0][0] == "Werkzeug"
    assert record.snapshot["tool"]["number"] in document["key_facts"][0][1]
    assert document["reason_note"] == record.data["other_reason"]
    html = client.get(f"/orders/sampling/{record.id}/print").get_data(as_text=True)
    assert 'Warum wird gemustert?' in html and 'key-facts' in html
    assert client.get(f"/orders/sampling/{record.id}/pdf").status_code == 200
    assert record.version == version_before
    assert record.data == data_before and record.snapshot == snapshot_before
    with app.test_request_context():
        dashboard = render_template("masterdata/materials/dashboard.html", can_create=True,
                                    can_edit=True, can_export=True, can_import=True)
        assert 'material_type=masterbatch' not in dashboard
        assert 'Masterbatch / Farbbatch</div>' not in dashboard
        assert 'Materialübersicht' in dashboard and '/masterdata/materials/list' in dashboard
    assert "masterbatch" in MATERIAL_TYPES  # Category not removed with the tile.
    # User text stays escaped; long explanations can split across PDF pages.
    record.data = {**record.data, "other_reason": ("Änderungsgrund <QS> & Werkzeugprüfung. " * 240) + "ENDE-ANLASS"}
    db.session.commit()
    html = client.get(f"/orders/sampling/{record.id}/print").get_data(as_text=True)
    assert '&lt;QS&gt;' in html and '<QS>' not in html
    pdf = build_pdf(record).getvalue()
    assert pdf.startswith(b'%PDF-')
    output = ROOT.parent / "header_pdf_qa"
    output.mkdir(exist_ok=True)
    (output / "sampling_long_reason.pdf").write_bytes(pdf)
print("PASS: one material overview, preserved masterbatch category, prominent reason/tool/article, one explanation field, unchanged saved records, print/PDF, escaped and long explanation.")
