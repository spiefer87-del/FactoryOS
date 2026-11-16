"""Synthetic regression: list rendering and optional, editable visual presets."""
import runpy
from pathlib import Path
from html.parser import HTMLParser
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_quality_plan.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.quality.inspection_plan.models import QualityInspectionPlan,QualityInspectionPlanVersion,QualityInspectionCheck,QualityInspectionChangeLog
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.quality.inspection_plan.visual_presets import visual_presets
from factoryos.modules.quality.inspection_plan.services.builder_service import revision_token

class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.tables=[];self.rows=0;self.headings=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag=='table':self.tables.append(attributes.get('id'))
        if tag=='tr' and 'data-search-text' in attributes:self.rows+=1
        if tag=='th':self.headings.append(attributes.get('data-col'))

with app.app_context():
    client=fixture['client'];new=db.session.merge(fixture['new']);tool=db.session.merge(fixture['tool'])
    for number in range(24):
        article=Article(article_no=f'LIST-{number:03d}',article_name='Prüfteil <script>alert(1)</script> '+str(number))
        db.session.add(article);db.session.flush();plan=QualityInspectionPlan(article_id=article.id,tool_id=tool.id);db.session.add(plan);db.session.flush()
        db.session.add(QualityInspectionPlanVersion(plan_id=plan.id,revision='1.0',status=['draft','review','released','closed'][number%4]))
    db.session.commit()
    for path in ('/quality/inspection-plans/inspectionplan','/quality/inspection-plans/dashboard'):
        response=client.get(path);assert response.status_code==200
        html=response.get_data(as_text=True);parser=TableParser();parser.feed(html)
        assert parser.tables==['quality-plans-table'] and parser.rows==25
        assert parser.headings==['tool_no','article_no','article_name','revision','status','modules','created','actions']
        assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
        assert 'data-quality-column' in html and 'fos-pagination' in html and 'type="search"' in html
    section=next(s for s in new.sections if s.section_type=='visual')
    before=(QualityInspectionCheck.query.count(),QualityInspectionChangeLog.query.count())
    response=client.get(f'/quality/inspection-plans/{new.plan_id}/version/{new.id}/edit');html=response.get_data(as_text=True)
    assert response.status_code==200 and 'data-visual-preset' in html
    presets=visual_presets();assert len(presets)>=10
    assert all(label in html for label in ('Grat / Schwimmhaut','Luftschlieren','Brenner / Brandstellen','Dieseleffekt'))
    assert before==(QualityInspectionCheck.query.count(),QualityInspectionChangeLog.query.count())
    with client.session_transaction() as session:csrf=session['access_csrf']
    data={key:presets[0][key] for key in ('name','requirement','method')}
    data['requirement']='Grat an Prüffläche A nicht zulässig; gemäß freigegebenem Grenzmuster QM-001.'
    response=client.post(f'/quality/inspection-plans/section/{section.id}/check',data={**data,'access_csrf':csrf,'revision_token':revision_token(new)})
    assert response.status_code==303
    saved=QualityInspectionCheck.query.filter_by(section_id=section.id,name=data['name']).one()
    assert saved.requirement==data['requirement']
print('PASS: both list URLs; 25 plans with latest revisions only; table/search/column/pagination hooks; escaped values; visual presets never save on GET; manually adapted preset persists through existing guarded workflow.')
