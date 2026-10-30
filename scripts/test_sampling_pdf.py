"""PDF/print regression checks using disposable, synthetic sampling records."""
import sys
import runpy
from pathlib import Path
from datetime import datetime
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / "scripts/test_sampling_orders.py"))
app = fixture["app"]
from factoryos.extensions import db
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.sampling.pdf_service import build_pdf
from factoryos.modules.sampling.document_service import document_data

output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
with app.app_context():
    record = SamplingOrder.query.filter_by(reason="repair").one()
    version_before = record.version
    client = app.test_client()
    assert client.get(f"/orders/sampling/{record.id}/pdf").status_code == 302
    assert client.get(f"/orders/sampling/{record.id}/print").status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(fixture["user"].id)
        session["_fresh"] = True
    assert client.get("/orders/sampling/999999/pdf").status_code == 404
    pdf_response = client.get(f"/orders/sampling/{record.id}/pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.data.startswith(b"%PDF-")
    assert pdf_response.mimetype == "application/pdf"
    assert "attachment;" in pdf_response.headers["Content-Disposition"]
    assert "no-store" in pdf_response.headers["Cache-Control"]
    html = client.get(f"/orders/sampling/{record.id}/print").get_data(as_text=True)
    assert "Jetzt drucken" in html and "window.print()" in html
    assert "Intern erfolgreich abgeschlossen" in html
    assert "class=\"sidebar\"" not in html
    assert record.version == version_before  # read-only export
    # Saved snapshots, not the newer master-data name changed in the fixture.
    assert "Neuer Stammdatenname" not in html
    if output:
        output.mkdir(parents=True, exist_ok=True)
        (output / "sampling_standard.pdf").write_bytes(pdf_response.data)
    # Initial, open and long/unbroken/multiline input; no clipping / LayoutError.
    initial = SamplingOrder.query.filter_by(reason="initial").one()
    initial.order.order_no = "M-2026-INITIAL"
    initial.state = "review"
    initial.completed_at = None
    initial.completed_by_id = None
    values = dict(initial.data)
    values.update(setup_minutes=0, sampling_minutes=0,
                  color="Natur / R&D <Material>",
                  instructions="Umlaute: ÄÖÜ äöü ß\nVorgaben zur Werkzeugreparatur und Farbänderung.",
                  changes_result="Muster geprüft. Maße und Oberfläche entsprechen den Vorgaben.",
                  cavity_result="Nest 1: Maße erfüllt. Nest 2: Maße erfüllt.")
    initial.data = values
    db.session.commit()
    normal = build_pdf(initial).getvalue()
    assert normal.startswith(b"%PDF-")
    assert document_data(initial)["groups"][2]["rows"][3][1] == "0"
    if output:
        (output / "sampling_initial.pdf").write_bytes(normal)
    values = dict(initial.data)
    values["changes_result"] = ("Langer Ergebnistext mit ÄÖÜ und <Tag> & Prüfung. " * 200)[:9900] + " ENDE-ERGEBNIS"
    initial.data = values
    initial.checks[0].note = ("Prüfnotiz " * 520)[:4900] + " ENDE-PRUEFNOTIZ"
    db.session.commit()
    long_pdf = build_pdf(initial).getvalue()
    assert long_pdf.startswith(b"%PDF-")
    html = client.get(f"/orders/sampling/{initial.id}/print").get_data(as_text=True)
    assert "&lt;Tag&gt;" in html and "<Tag>" not in html
    assert "BEARBEITUNGSSTAND" in html
    if output:
        (output / "sampling_long.pdf").write_bytes(long_pdf)
print("PASS: authenticated PDF/download/print routes, 404, cache policy, readonly version, snapshots, initial status, zero values, umlauts, long text and HTML escaping.")
