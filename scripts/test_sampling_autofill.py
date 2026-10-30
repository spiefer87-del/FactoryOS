"""Autofill and material-change safeguards; isolated in-memory test database."""
import sys
import runpy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture = runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.modules.sampling.autofill_service import article_defaults, autofill_catalog, material_confirmed
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.sampling.service import save_sampling, completion_errors
from werkzeug.datastructures import MultiDict
with app.app_context():
    for key in ("article", "customer", "material", "tool", "machine", "user"):
        fixture[key] = db.session.merge(fixture[key])
    article=fixture["article"]
    article.customer=fixture["customer"]
    article.material=fixture["material"]
    article.tools=[fixture["tool"]]
    article.cycle_time_s=12.5
    fixture["material"].color="Natur"
    db.session.commit()
    defaults=article_defaults(article)
    assert defaults["customer_id"]==str(fixture["customer"].id)
    assert defaults["tool_id"]==str(fixture["tool"].id)
    assert defaults["material_id"]==str(fixture["material"].id)
    assert defaults["reference"]["Zykluszeit laut Artikel (s)"]==12.5
    another=Tool(tool_no="W002",name="Zweites Werkzeug")
    article.tools.append(another)
    db.session.commit()
    assert article_defaults(article)["tool_id"]==""
    assert article_defaults(article)["tool_count"]==2
    record=SamplingOrder.query.filter_by(reason="material_change").one()
    form=dict(order_no="MATERIAL-CONFIRM", reason="material_change", target_qty="1", state="draft",
              article_id=str(article.id), tool_id=str(fixture["tool"].id),
              customer_id=str(fixture["customer"].id), material_id=str(fixture["material"].id))
    with app.test_request_context():
        try:
            save_sampling(MultiDict(form),fixture["user"].id)
        except ValueError as exc:
            db.session.rollback()
            assert "bestätigen" in str(exc)
        else:
            raise AssertionError("Unconfirmed material accepted")
        form["material_confirmed"]="yes"
        saved=save_sampling(MultiDict(form),fixture["user"].id)
        assert material_confirmed(saved)
        assert saved.snapshot["reference"]["Zykluszeit laut Artikel (s)"]==12.5
        # Defaults are references, never silently made into measured values.
        assert saved.data["cycle_seconds"] is None
        assert saved.data["shot_weight"] is None
        saved.data={}
        db.session.commit()
        assert not material_confirmed(saved)
        assert any("Versuchsmaterial" in e for e in completion_errors(saved))
    client=app.test_client()
    with client.session_transaction() as session:
        session["_user_id"]=str(fixture["user"].id)
        session["_fresh"]=True
    html=client.get("/orders/sampling/create").get_data(as_text=True)
    assert "sampling-autofill-data" in html and "Werkstoffänderung" in html
    assert "material_confirmed" in html and "sampling_autofill.js" in html
print("PASS: unique/multiple tools, reference suggestions, explicit material confirmation, saved reference snapshot, no invented measured values, rendered form.")

