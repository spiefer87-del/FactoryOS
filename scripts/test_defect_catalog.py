"""Synthetic reset + article-photo workflow. Never production data."""
import runpy,tempfile,sqlite3
from pathlib import Path
from io import BytesIO
from PIL import Image
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.article_defects.models import ArticleDefect,ArticleDefectPhoto,InspectionResetRun
from factoryos.modules.quality.inspection_plan.models import QualityInspectionPlan,QualityInspectionPlanVersion,QualityInspectionSection,QualityInspectionCheck
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.orders.models import Order
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from scripts.upgrade_defect_catalog import run_upgrade
from scripts.reset_test_inspection_plans import run_reset
from factoryos.modules.article_defects.routes import photo_root
from factoryos.modules.article_defects.photos import MAX_EDGE,MAX_STORED_BYTES

with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article']);tool=db.session.merge(fixture['tool'])
    from sqlalchemy import text,inspect
    db.session.execute(text('ALTER TABLE article_defects DROP COLUMN tool_no'));db.session.commit()
    run_upgrade(True);run_upgrade();run_upgrade()
    assert 'tool_no' in {c['name'] for c in inspect(db.engine).get_columns('article_defects')}
    if tool not in article.tools:article.tools.append(tool);db.session.commit()
    plan=QualityInspectionPlan(article_id=article.id,tool_id=tool.id);db.session.add(plan);db.session.flush()
    version=QualityInspectionPlanVersion(plan_id=plan.id,revision='1.0',status='released');db.session.add(version);db.session.flush()
    section=QualityInspectionSection(plan_version_id=version.id,title='Testmodul',section_type='visual');db.session.add(section);db.session.flush()
    db.session.add(QualityInspectionCheck(section_id=section.id,name='Grat',requirement='Test',method='Sichtvergleich',sort_order=1));db.session.commit()
    counts=(Article.query.count(),Tool.query.count(),Order.query.count())
    preview=run_reset();assert preview['qm_plans']==1 and QualityInspectionPlan.query.count()==1
    try:run_reset(None,True);assert False
    except ValueError:db.session.rollback()
    folder=Path(tempfile.mkdtemp(prefix='quality_reset_test_',dir=Path(__file__).resolve().parents[2]));backup=folder/'backup.db'
    db.session.commit();connection=sqlite3.connect(backup)
    raw=db.engine.raw_connection();raw.driver_connection.backup(connection);connection.close();raw.close()
    section.title='Geänderter Inhalt bei gleicher Zeilenzahl';db.session.commit()
    try:run_reset(str(backup),True);assert False,'Abweichende Sicherung wurde angenommen'
    except ValueError:db.session.rollback()
    assert QualityInspectionPlan.query.count()==1
    section.title='Testmodul';db.session.commit()
    run_reset(str(backup),True)
    assert QualityInspectionPlan.query.count()==0 and QualityInspectionPlanVersion.query.count()==0 and QualityInspectionCheck.query.count()==0
    assert counts==(Article.query.count(),Tool.query.count(),Order.query.count())
    assert InspectionResetRun.query.count()==1
    for removed in (plan,version,section):db.session.expunge(removed)
    new=QualityInspectionPlan(article_id=article.id,tool_id=tool.id);db.session.add(new);db.session.commit()
    run_reset(str(backup),True);assert QualityInspectionPlan.query.count()==1
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    page=client.get('/quality/defect-catalog/create?article_id='+str(article.id));assert page.status_code==200,page.get_data(as_text=True)[:500]
    with client.session_transaction() as session:csrf=session['access_csrf']
    assert 'capture="environment"' in page.get_data(as_text=True)
    assert '<option value="">Bitte Fehlerart auswählen</option>' in page.get_data(as_text=True)
    data=dict(access_csrf=csrf,article_id=str(article.id),title='Grat links',defect_type='Grat / Schwimmhaut',description='Grat an der linken Trennkante bei Produktion beobachtet.',remedy='Bisher keine bestätigte Abhilfe.')
    assert 'defect-article-tools' in page.get_data(as_text=True)
    assert client.post('/quality/defect-catalog/create',data={**data,'tool_no':'UNKNOWN-TOOL'}).status_code==422
    data['tool_no']=tool.tool_no
    existing_files=set(photo_root().glob('*'))
    image=BytesIO();Image.new('RGB',(2400,1800),'white').save(image,'PNG');image.seek(0)
    response=client.post('/quality/defect-catalog/create',data={**data,'camera':(image,'photo.png')});assert response.status_code==303,response.get_data(as_text=True)[:1000]
    entry=ArticleDefect.query.one();photo=ArticleDefectPhoto.query.one();assert entry.article_id==article.id
    assert entry.tool_no==tool.tool_no
    assert tool.tool_no in client.get(f'/quality/defect-catalog/{entry.id}').get_data(as_text=True)
    saved=photo_root()/photo.filename
    assert saved.stat().st_size<=MAX_STORED_BYTES
    assert set(photo_root().glob('*'))-existing_files=={saved},'Original zusätzlich gespeichert'
    with Image.open(saved) as stored:
        assert stored.format=='JPEG' and max(stored.size)<=MAX_EDGE and not stored.getexif()
    assert client.get(f'/quality/defect-catalog/{entry.id}').status_code==200
    assert client.get(f'/quality/defect-catalog/photo/{photo.id}').mimetype=='image/jpeg'
    count=ArticleDefect.query.count();response=client.post('/quality/defect-catalog/create',data={**data,'photo':(BytesIO(b'bad'),'bad.png')});assert response.status_code==422 and ArticleDefect.query.count()==count
    version=entry.version
    response=client.post(f'/quality/defect-catalog/{entry.id}/edit',data={**data,'version':version,'archived':'yes'});assert response.status_code==303 and entry.archived
    assert client.post(f'/quality/defect-catalog/{entry.id}/edit',data={**data,'version':version}).status_code==409
    assert client.post('/quality/defect-catalog/create',data={}).status_code==400
    assert client.post('/quality/defect-catalog/create',data={**data,'tool_no':''}).status_code==303
    assert client.get('/quality/complaints/').status_code==200
    assert 'Fehlerkatalog' in client.get('/quality/dashboard').get_data(as_text=True)
    assert '/quality/defect-catalog/?article_id=' in client.get(f'/masterdata/articles/{article.id}').get_data(as_text=True)
    reader=User(username='defects-denied',password_hash='unused',active=True,role=Role(name='defects-denied',active=True));db.session.add(reader);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    assert denied.get('/quality/defect-catalog/').status_code==403 and denied.get(f'/quality/defect-catalog/photo/{photo.id}').status_code==403
    assert denied.post('/quality/defect-catalog/create',data=data).status_code==403
    delete_url=f'/quality/defect-catalog/photo/{photo.id}/delete'
    assert client.get(delete_url).status_code==405
    assert client.post(delete_url,data={}).status_code==400
    assert denied.post(delete_url,data={'access_csrf':csrf,'version':entry.version}).status_code==403
    reader.role.permissions.append(Permission.query.filter_by(name='defects.view').one());db.session.commit()
    assert denied.get('/quality/defect-catalog/').status_code==200
    assert denied.get(f'/quality/defect-catalog/photo/{photo.id}').status_code==200
    assert denied.get(f'/quality/defect-catalog/{entry.id}/edit').status_code==403
    assert denied.post('/quality/defect-catalog/create',data=data).status_code==403
    reader.role.permissions.append(Permission.query.filter_by(name='defects.edit').one());db.session.commit()
    assert denied.post(delete_url,data={'access_csrf':csrf,'version':entry.version}).status_code==403
    assert client.post(delete_url,data={'access_csrf':csrf,'version':0}).status_code==409
    assert saved.is_file()
    assert client.post(delete_url,data={'access_csrf':csrf,'version':entry.version}).status_code==303
    assert not saved.exists() and db.session.get(ArticleDefectPhoto,photo.id) is None
    assert client.get(f'/quality/defect-catalog/photo/{photo.id}').status_code==404
    assert db.session.get(ArticleDefect,entry.id) is not None
print('PASS: reset preview and verified backup; all test revisions removed; other data preserved; reset once/new plans survive; camera upload, invalid image rejection, article binding, archive/stale edit, CSRF, private photo ACL, quality categories and article link.')
