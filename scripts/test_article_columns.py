"""Template/column structure using an isolated SQLite fixture."""
import sys
import runpy
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture=runpy.run_path(str(ROOT/"scripts/test_article_sampling_history.py"))
app=fixture["app"]
from factoryos.models.user import User


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside=False
        self.headers=[]
        self.rows=[]
        self.current=[]
        self.links=[]
        self.toggles=[]
        self.scroll_region=None
        self.scroll_hint=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if "article-table-scroll" in attrs.get("class","").split():
            self.scroll_region=attrs
        if attrs.get("id")=="article-table-scroll-hint": self.scroll_hint=True
        if tag=="table" and attrs.get("id")=="articles-table": self.inside=True
        if tag=="input" and "data-article-column-toggle" in attrs: self.toggles.append(attrs)
        if not self.inside: return
        if tag=="tr": self.current=[]
        if tag=="th": self.headers.append(attrs.get("data-article-column"))
        if tag=="td": self.current.append(attrs.get("data-article-column"))
        if tag=="a": self.links.append(attrs)
    def handle_endtag(self,tag):
        if tag=="tr" and self.inside and self.current: self.rows.append(self.current)
        if tag=="table": self.inside=False


with app.app_context():
    client=app.test_client()
    with client.session_transaction() as session:
        session["_user_id"]=str(User.query.filter_by(username="test").one().id)
        session["_fresh"]=True
    response=client.get("/masterdata/articles/list")
    assert response.status_code==200
    html=response.get_data(as_text=True)
    parser=TableParser();parser.feed(html)
    expected=["article_no","article_name","customer","material","tools","status","sampling","actions"]
    assert parser.headers==expected
    assert parser.rows and all(row==expected for row in parser.rows)
    assert [t["data-article-column-toggle"] for t in parser.toggles]==expected
    assert "disabled" in parser.toggles[0]
    assert 'id="article-columns-reset"' in html and 'js/article_columns.js' in html
    assert any("article-number-chip" in link.get("class","") for link in parser.links)
    for link in parser.links:
        if "/customers/" in link.get("href","") or "/materials/" in link.get("href",""):
            assert "article-link-chip" in link["class"]
    assert "&lt;QS&gt;" in html
    assert parser.scroll_hint and parser.scroll_region
    assert parser.scroll_region["tabindex"]=="0" and parser.scroll_region["role"]=="region"
    assert parser.scroll_region["aria-describedby"]=="article-table-scroll-hint"
    assert "js/article_table_scroll.js" in html
    assert client.get("/static/js/article_table_scroll.js").status_code==200
    assert client.get("/static/css/article_overview.css").status_code==200
print("PASS: eight stable table headers/cells, column controls, reset, required identity, chip links, existing history and escaping.")
