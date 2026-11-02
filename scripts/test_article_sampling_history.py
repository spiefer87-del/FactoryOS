"""Isolated article overview/history reads. Never connects to the Raspberry DB."""
import sys
import runpy
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import event
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
fixture = runpy.run_path(str(ROOT / "scripts/test_sampling_orders.py"))
app = fixture["app"]
from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.orders.models import Order
from factoryos.modules.sampling.models import SamplingOrder, SamplingCheck
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.masterdata.articles.queries.sampling_queries import sampling_summaries

with app.app_context():
    user = db.session.merge(fixture["user"])
    article = Article(article_no="HISTORY-ARTICLE", article_name="Deckel <QS>")
    other = Article(article_no="OTHER-ARTICLE", article_name="Fremdartikel")
    empty = Article(article_no="EMPTY-ARTICLE", article_name="Ohne Musterung")
    db.session.add_all([article, other, empty])
    db.session.flush()
    records = []
    for index, state in enumerate(("draft", "in_progress", "review", "rework", "completed")):
        record = SamplingOrder(order=Order(order_no="HISTORY-" + state, target_qty=1),
            article_id=article.id, state=state, reason="repair", created_by_id=user.id,
            created_at=datetime(2026, 1, 1) + timedelta(days=index),
            data={"changes_result": "Ergebnis <script>BAD</script>", "other_reason": "Werkzeug repariert"},
            snapshot={"tool": {"number": "HISTORICAL-TOOL", "name": "Gespeicherter Werkzeugstand"}})
        record.checks = [SamplingCheck(key="external", status="open")]
        records.append(record)
    db.session.add_all(records)
    db.session.add(SamplingOrder(order=Order(order_no="FOREIGN-SAMPLING", target_qty=1), article_id=other.id,
        state="draft", reason="initial", created_by_id=user.id, data={}, snapshot={}))
    db.session.add_all([
        ChangeLog(entity_type="article",entity_id=article.id,action="update",entity_name="Alter Artikelname",changes={"article_name":{"old":"Früher","new":"Heute <QS>"}},user_id=user.id),
        ChangeLog(entity_type="article",entity_id=other.id,action="update",changes={"note":"FOREIGN-LOG"}),
    ])
    db.session.commit()
    statements = []
    def count_statements(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(db.engine, "before_cursor_execute", count_statements)
    ids = [article.id, other.id, empty.id]  # Resolve expired IDs before measuring.
    statements.clear()
    summary = sampling_summaries(ids)
    assert len(statements) == 1
    event.remove(db.engine, "before_cursor_execute", count_statements)
    assert summary[article.id]["open_count"] == 4
    assert summary[article.id]["total"] == 5
    assert summary[other.id]["open_count"] == 1
    assert summary[empty.id]["open_count"] == 0
    assert sampling_summaries([]) == {}
    client = app.test_client()
    url = f"/masterdata/articles/{article.id}/history"
    assert client.get(url).status_code == 302
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
    assert client.get("/masterdata/articles/999999/history").status_code == 404
    before = [(r.id, r.version, dict(r.data)) for r in records]
    response = client.get(url)
    assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
    html = response.get_data(as_text=True)
    assert "4 offene Musterungen" in html
    assert "FOREIGN-SAMPLING" not in html and "FOREIGN-LOG" not in html
    assert "HISTORICAL-TOOL" in html and "Gespeicherter Werkzeugstand" in html
    assert "Intern erfolgreich abgeschlossen" in html and "Kunde: Offen" in html
    assert "&lt;script&gt;BAD&lt;/script&gt;" in html and "<script>BAD</script>" not in html
    assert "Alter Artikelname" in html
    assert html.index("HISTORY-completed") < html.index("HISTORY-draft")
    assert [(r.id, r.version, dict(r.data)) for r in records] == before
    listing = client.get("/masterdata/articles/list").get_data(as_text=True)
    assert "<th>Musterung</th>" in listing and "4 offene Musterungen" in listing
    assert "Keine offene Musterung" in listing and "data-article-history-popup" in listing
    detail = client.get(f"/masterdata/articles/{article.id}").get_data(as_text=True)
    assert url in detail and "Musterungs- / Artikelhistorie öffnen" in detail
    no_history = client.get(f"/masterdata/articles/{empty.id}/history").get_data(as_text=True)
    assert "noch keine Musterungsaufträge" in no_history
    assert client.get(url + "?sampling_page=bad&log_page=-5").status_code == 200
    # Paginate both timelines independently, never silently truncate old events.
    for i in range(23):
        db.session.add(SamplingOrder(order=Order(order_no=f"PAGED-{i}",target_qty=1),
            article_id=article.id,state="draft",reason="repair",created_by_id=user.id,data={},snapshot={}))
        db.session.add(ChangeLog(entity_type="article",entity_id=article.id,action="update",changes={"sequence":i}))
    db.session.commit()
    page = client.get(url + "?sampling_page=2&log_page=2").get_data(as_text=True)
    assert "Seite 2 von 2" in page
    assert "sampling_page=1" in page and "log_page=1" in page
    assert "HISTORY-draft" in page
print("PASS: one aggregate query, all open states, completed/customer distinction, stable article IDs, auth/404, read-only history, saved tool snapshots, escaping, empty state, pagination, overview and detail links.")
