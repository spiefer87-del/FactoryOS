"""Two independent requests must not create duplicate successor revisions."""
import runpy
import threading
from pathlib import Path
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_machine_control_concurrency.py'))
app=fixture['app'];app.config.update(TESTING=True,SESSION_COOKIE_SECURE=False)
from factoryos.extensions import db
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.quality.inspection_plan.models import QualityInspectionPlan, QualityInspectionPlanVersion
from factoryos.modules.quality.inspection_plan.services.builder_service import revision_token
with app.app_context():
    article=Article(article_no='QM-RACE',article_name='Prüfteil');tool=Tool(tool_no='QM-RACE',name='Werkzeug')
    db.session.add_all([article,tool]);db.session.flush()
    plan=QualityInspectionPlan(article_id=article.id,tool_id=tool.id);db.session.add(plan);db.session.flush()
    source=QualityInspectionPlanVersion(plan_id=plan.id,revision='1.0',status='released');db.session.add(source);db.session.commit()
    source_id=source.id;plan_id=plan.id;token=revision_token(source)
barrier=threading.Barrier(2);results=[];errors=[]
def worker():
    try:
        client=app.test_client()
        with client.session_transaction() as session:session['_user_id']=str(fixture['uid']);session['_fresh']=True
        assert client.get(f'/quality/inspection-plans/{plan_id}/version/{source_id}/edit').status_code==200
        with client.session_transaction() as session:csrf=session['access_csrf']
        barrier.wait(timeout=10)
        results.append(client.post(f'/quality/inspection-plans/{source_id}/new_revision',data={'access_csrf':csrf,'revision_token':token}).status_code)
    except Exception as error:errors.append(repr(error))
threads=[threading.Thread(target=worker) for _ in range(2)]
for thread in threads:thread.start()
for thread in threads:thread.join(timeout=25)
assert not any(t.is_alive() for t in threads),'Deadlock'
assert not errors,errors
assert sorted(results)==[303,409],results
with app.app_context():
    assert QualityInspectionPlanVersion.query.filter_by(plan_id=plan_id).count()==2
    assert QualityInspectionPlanVersion.query.filter_by(plan_id=plan_id,revision='1.1').count()==1
    assert db.session.get(QualityInspectionPlanVersion,source_id).status=='released'
print('PASS: simultaneous new-revision requests produce exactly one successor; loser receives conflict; source stays released; no deadlock.')
