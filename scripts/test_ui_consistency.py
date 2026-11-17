"""Rendered UI regressions with isolated synthetic data, never the Raspberry DB."""
import runpy
from html.parser import HTMLParser
from pathlib import Path
from flask import url_for

fixture=runpy.run_path(str(Path(__file__).with_name('test_sampling_orders.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.article_defects.models import ArticleDefect,ArticleDefectPhoto
from factoryos.modules.orders.models import Order
from factoryos.modules.projects.workspace_models import Workspace,Member
from factoryos.modules.masterdata.articles.models import Article


class Catalog(HTMLParser):
    def __init__(self,html):
        super().__init__();self.cell=0;self.rows=[];self.current=None;self.links=[];self.classes=[]
        self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='tr' and 'data-search-text' in attrs:self.current=[];self.cell=0
        if tag=='td' and self.current is not None:self.cell+=1
        if tag=='a':
            self.links.append(attrs)
            if self.current is not None:self.current.append((self.cell,attrs))
    def handle_endtag(self,tag):
        if tag=='tr' and self.current is not None:self.rows.append(self.current);self.current=None


with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article'])
    entries=[]
    for index in range(12):
        entry=ArticleDefect(article_id=article.id,created_by_id=user.id,title=f'Farbfehler {index:02d}',
            defect_type='Farbabweichungen / Farbschlieren',description=f'Suchbegriff {index:02d}',remedy='Farbe prüfen',archived=False)
        db.session.add(entry);entries.append(entry)
    project=Order(order_no='UI-PROJECT',description='UI-Prüfung',status='offen',is_project=True,project_leader_id=user.id)
    db.session.add(project);db.session.flush()
    db.session.add_all([Workspace(order_id=project.id,project_kind='other'),Member(project_id=project.id,user_id=user.id)])
    photo=ArticleDefectPhoto(defect_id=entries[0].id,filename='ui-test.jpg');db.session.add(photo);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    with app.test_request_context():
        paths={'quality':url_for('quality.dashboard'),'production':url_for('production.dashboard'),
            'catalog':url_for('article_defects.overview'),'detail':url_for('article_defects.detail',entry_id=entries[0].id),
            'projects':url_for('projects.dashboard')}
    pages={}
    for name,path in paths.items():
        response=client.get(path)
        assert response.status_code==200,(name,response.status_code)
        pages[name]=response.get_data(as_text=True)
        assert 'css/ui_consistency.css' in pages[name]
    quality=pages['quality']
    assert 'dashboard-card-icon' not in quality and 'dashboard-card-title' not in quality
    assert 'class="card-icon"' in quality and 'class="card-title"' in quality and 'class="card-desc"' in quality
    assert 'aria-disabled="true"' in quality and 'href="#"' not in quality
    catalog=Catalog(pages['catalog'])
    assert len(catalog.rows)==12
    for row in catalog.rows:
        assert row and row[0][0]==1 and row[0][1].get('class')=='defect-entry-link'
        assert '/quality/defect-catalog/' in row[0][1]['href']
        assert row[0][1].get('aria-label','').endswith('Katalogeintrag öffnen')
    back=[a for a in catalog.links if a.get('href')==paths['quality']]
    assert any(a.get('class')=='btn-secondary' for a in back)
    assert 'data-label="Fehlerart"' in pages['catalog'] and 'defect-catalog-sort' in pages['catalog']
    assert 'class="btn-primary">Suchen' in pages['projects'] and 'class="ui-link"' in pages['projects']
    detail=Catalog(pages['detail'])
    assert any('/photo/' in a.get('href','') and not a.get('class') for a in detail.links)
    # Optional fixture export for actual DOM/stylesheet interaction checks.
    import os,json
    destination=os.environ.get('FACTORYOS_UI_TEST_EXPORT')
    if destination:
        folder=Path(destination);folder.mkdir(parents=True,exist_ok=True)
        for name,html in pages.items():(folder/(name+'.html')).write_text(html)
        (folder/'links.json').write_text(json.dumps({'quality':paths['quality'],'detail':paths['detail']}))
    print('PASS: shared dashboard classes, disabled tile semantics, rounded navigation and project controls, first-column detail links for all catalog entries, mobile metadata, preserved photo preview links, existing page permissions')
