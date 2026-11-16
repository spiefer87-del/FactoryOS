"""Synthetic page regression, no production database."""
import runpy
from pathlib import Path
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.quality.inspection_plan.models import QualityInspectionPlan
with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article']);tool=db.session.merge(fixture['tool'])
    if tool not in article.tools:article.tools.append(tool);db.session.commit()
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    before=QualityInspectionPlan.query.count()
    response=client.get('/quality/inspection-plans/create');html=response.get_data(as_text=True)
    assert response.status_code==200
    assert all(value in html for value in ('id="article-search"','name="article_id"','name="tool_id"','access_csrf','quality_create.css','quality_create.js'))
    response=client.get(f'/quality/inspection-plans/tools-by-article/{article.id}')
    assert response.status_code==200 and any(str(row['id'])==str(tool.id) for row in response.json)
    assert QualityInspectionPlan.query.count()==before
print('PASS: search/mobile assets rendered, original form field names and CSRF retained, same article-tool endpoint, GET creates no plan.')
