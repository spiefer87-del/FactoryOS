"""Isolated master-data, recipe, sampling, migration and print regression checks."""
import runpy
import sys
from pathlib import Path
from io import BytesIO
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / "scripts/test_sampling_orders.py"))
app = fixture["app"]
from factoryos.extensions import db
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.articles.services.article_service import create_article, update_article, color_data
from factoryos.modules.masterdata.materials.services.material_service import material_data_from_input, ensure_batch_category
from factoryos.modules.masterdata.materials.services.material_excel_service import _canonical_row, EXPECTED_HEADERS, TYPE_ALIASES, _material_values
from factoryos.modules.sampling.autofill_service import article_defaults, color_confirmed
from factoryos.modules.sampling.service import save_sampling, completion_errors
from factoryos.modules.sampling.document_service import document_data
from factoryos.modules.sampling.pdf_service import build_pdf
from werkzeug.datastructures import MultiDict
from flask import Flask


def formdata(*args, **kwargs):
    return MultiDict(kwargs) if kwargs else MultiDict(*args)

from sqlalchemy import text, inspect
from scripts.upgrade_masterbatch import run_upgrade


def rejects(fn, text_hint):
    try:
        fn()
    except ValueError as exc:
        assert text_hint in str(exc), str(exc)
        db.session.rollback()
    else:
        raise AssertionError("Expected validation failure: " + text_hint)


with app.app_context(), app.test_request_context():
    for key in ("user", "material"):
        fixture[key] = db.session.merge(fixture[key])
    uid = fixture["user"].id
    batch = Material(**material_data_from_input(dict(material_no="B-01", name="Farbkonzentrat", material_type="masterbatch", color="Lichtgrau", ral_color="RAL 7035")))
    db.session.add(batch)
    db.session.commit()
    assert batch.polymer_type is None  # No mandatory resin type for batch.
    assert _canonical_row(dict(material_no="B-EXCEL", name="Excelbatch", material_type="Masterbatch / Farbbatch", ral_color="RAL 9005"))["material_type"] == "masterbatch"
    assert "ral_color" in EXPECTED_HEADERS
    # Test export-to-import mapping without authoring a separate workbook.
    assert _canonical_row(_material_values(batch))["ral_color"] == "RAL 7035"
    form = formdata(article_no="A-BATCH", article_name="Farbartikel", masterbatch_id=str(batch.id), masterbatch_percent="2,5")
    article = create_article(form)
    assert article.masterbatch_id == batch.id and article.masterbatch_percent == 2.5
    defaults = article_defaults(article)
    assert defaults["color"] == "Lichtgrau" and defaults["ral_color"] == "RAL 7035"
    assert defaults["masterbatch_id"] == str(batch.id)
    for bad in ("-1", "101", "nan", "inf", "abc"):
        rejects(lambda: color_data(formdata(masterbatch_id=str(batch.id), masterbatch_percent=bad)), "0 und 100")
    assert color_data(formdata(masterbatch_percent="0"))["masterbatch_percent"] == 0
    rejects(lambda: color_data(formdata(masterbatch_id=str(fixture["material"].id))), "Kategorie Masterbatch")
    rejects(lambda: ensure_batch_category(batch, "plastic"), "umgewandelt")
    saved_form = dict(order_no="COLOR-BATCH", reason="color_change", target_qty="1", state="draft", article_id=str(article.id),
                      masterbatch_id=str(batch.id), masterbatch_percent="2,5", color="Lichtgrau", ral_color="RAL 7035")
    rejects(lambda: save_sampling(formdata(saved_form), uid), "bestätigen")
    saved_form["color_confirmed"] = "yes"
    for invalid_percent in ("101", "nan", "-1", "inf"):
        rejects(lambda: save_sampling(formdata({**saved_form, "masterbatch_percent": invalid_percent}), uid), "Zahlenwert" if invalid_percent != "101" else "0 und 100")
    saved = save_sampling(formdata(saved_form), uid)
    assert color_confirmed(saved) and saved.data["masterbatch_percent"] == 2.5
    assert saved.data["masterbatch"] == "B-01 / Farbkonzentrat"
    assert not any("Farbänderung" in e for e in completion_errors(saved))
    saved.data = {**saved.data, "masterbatch_percent": 3}
    db.session.commit()
    assert not color_confirmed(saved)
    assert any("Farbänderung" in e for e in completion_errors(saved))
    # Same selection preserves old order designation; master change affects only new suggestions.
    batch.name = "Neue Bezeichnung"
    batch.color = "Geänderte Stammdatenfarbe"
    db.session.commit()
    saved_form["version"] = str(saved.version)
    saved = save_sampling(formdata(saved_form), uid, saved)
    assert saved.data["masterbatch"] == "B-01 / Farbkonzentrat"
    assert saved.data["color"] == "Lichtgrau"
    rows = dict(document_data(saved)["groups"][0]["rows"])
    assert rows["Gewünschter Farbton / RAL"] == "RAL 7035"
    assert rows["Farbbatch-Zugabe (% vom Hauptrohstoffgewicht)"] == "2,5"
    output = ROOT.parent / "masterbatch_qa"
    output.mkdir(exist_ok=True)
    (output / "sampling_masterbatch.pdf").write_bytes(build_pdf(saved).getvalue())
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(uid)
        session["_fresh"] = True
    html = client.get("/orders/sampling/create").get_data(as_text=True)
    assert html.count('name="masterbatch_id"') == 1
    assert html.count('name="masterbatch_percent"') == 1
    assert 'id="color_confirmed"' in html
    assert "RAL 7035" in client.get(f"/orders/sampling/{saved.id}/print").get_data(as_text=True)
    assert "Farbbatch" in client.get(f"/masterdata/articles/edit/{article.id}").get_data(as_text=True)
    assert "Geänderte Stammdatenfarbe" in client.get(f"/masterdata/articles/{article.id}").get_data(as_text=True)
    # Editable records keep old confirmations only while all relevant values match.
    update_article(article, formdata(article_no=article.article_no, article_name=article.article_name, masterbatch_id="", masterbatch_percent=""))
    assert article.masterbatch_id is None and article.masterbatch_percent is None

# Exercise the actual ADD COLUMN path on old raw SQLite tables, twice.
migration_app = Flask("masterbatch_upgrade_test")
migration_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
db.init_app(migration_app)
with migration_app.app_context():
    with db.engine.begin() as conn:
        conn.execute(text("CREATE TABLE materials (id INTEGER PRIMARY KEY, material_type TEXT)"))
        conn.execute(text("CREATE TABLE articles (id INTEGER PRIMARY KEY, material_id INTEGER, article_no TEXT)"))
        conn.execute(text("INSERT INTO articles VALUES (1,NULL,'LEGACY-ARTICLE')"))
    run_upgrade(True)
    assert "masterbatch_id" not in {c["name"] for c in inspect(db.engine).get_columns("articles")}
    run_upgrade()
    run_upgrade()
    with db.engine.connect() as conn:
        assert conn.execute(text("SELECT article_no,masterbatch_id,masterbatch_percent FROM articles")).one() == ("LEGACY-ARTICLE", None, None)
print("PASS: central masterbatch category/color/RAL, article links/dosage, validation, reason-specific confirmation, snapshots, form/detail/print/PDF, idempotent legacy migration.")
