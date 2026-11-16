"""Isolated end-to-end builder/workflow regression, never the production DB."""
import runpy
import tempfile
from pathlib import Path
from io import BytesIO
from datetime import date,timedelta
from PIL import Image
from sqlalchemy import text
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
app.static_folder=tempfile.mkdtemp(prefix='quality_test_media_',dir=str(Path(__file__).resolve().parents[2]))
from factoryos.extensions import db
from factoryos.modules.quality.inspection_plan.models import *
from factoryos.modules.quality.inspection_plan.services.builder_service import revision_token
from factoryos.modules.quality.inspection_plan.services.pdf_service import generate_inspection_plan_pdf
from factoryos.modules.quality.inspection_plan.definitions import MODULES
from factoryos.modules.quality.gauges.models import Gauge
from scripts.upgrade_quality_plan import run_upgrade

with app.app_context():
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article']);tool=db.session.merge(fixture['tool'])
    plan=QualityInspectionPlan(article_id=article.id,tool_id=tool.id,created_by_id=user.id)
    db.session.add(plan);db.session.flush()
    version=QualityInspectionPlanVersion(plan_id=plan.id,revision='1.0',status='draft')
    gauge=Gauge(gauge_no='QM-TEST',name='Grenzlehre',status='active',next_calibration=date.today()+timedelta(days=30))
    db.session.add_all([version,gauge]);db.session.commit()
    # Simulate the old schema and upgrade twice, preserving the existing plan.
    QualityInspectionCheck.__table__.drop(bind=db.engine)
    db.session.execute(text('ALTER TABLE qm_sections DROP COLUMN inspection_settings'));db.session.commit()
    run_upgrade(True);run_upgrade();run_upgrade()
    assert version.status=='draft' and version.revision=='1.0'
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
    def url(v=version):return f'/quality/inspection-plans/{v.plan_id}/version/{v.id}/edit'
    page=client.get(url());assert page.status_code==200,page.get_data(as_text=True)[:500]
    assert 'workflow-steps' in page.get_data(as_text=True)
    with client.session_transaction() as session:csrf=session['access_csrf']
    def post(path, data=None, v=version, expected=303):
        db.session.expire_all()
        response=client.post(path,data={'access_csrf':csrf,'revision_token':revision_token(v),**(data or {})})
        assert response.status_code==expected,(path,response.status_code,response.get_data(as_text=True)[:1500])
        db.session.expire_all();return response
    assert client.post(url(),data={'add_section_type':'visual'}).status_code==400
    post(url(),{'add_section_type':'not-a-module'},expected=422)
    for kind in MODULES:post(url(),{'add_section_type':kind})
    assert len(version.sections)==len(MODULES)
    post(url(),{'workflow_action':'review'},expected=422)
    for section in version.sections:
        prefix=f'/quality/inspection-plans/section/{section.id}'
        post(prefix+'/settings',{'title':section.title,'frequency':'Anfahren und alle 2 Stunden','sample_size':'3 Teile pro Nest','responsible':'Einrichter / QS','instructions':'Bei Abweichung sperren und QS informieren.'})
        if section.section_type=='dimension':
            post(prefix+'/characteristic',{'name':'Breite','target_value':'25,0','tolerance_minus':'0,1','tolerance_plus':'0,1','unit':'mm'})
        elif section.section_type=='gauge':
            post(prefix+'/gauge',{'name':'Passung','method':'Gutseite passt, Ausschussseite passt nicht','gauge_id':gauge.id})
        else:
            data={'name':'Merkmal '+section.section_type,'requirement':'Keine Abweichung gegenüber freigegebener Zeichnung <A> & Muster','method':'Vergleich mit Referenzmuster'}
            if section.section_type=='weight':
                invalid={**data,'target_value':'abc','tolerance_minus':'0,2','tolerance_plus':'0,2','unit':'g'}
                failed=post(prefix+'/check',invalid,expected=422)
                assert 'aria-invalid="true"' in failed.get_data(as_text=True) and 'abc' in failed.get_data(as_text=True)
                data.update(target_value='25,5',tolerance_minus='0,2',tolerance_plus='0,2',unit='g')
            post(prefix+'/check',data)
    # References with identical upload names must never overwrite older revisions.
    identification=next(s for s in version.sections if s.section_type=='identification')
    for color in ('red','blue'):
        photo=BytesIO();Image.new('RGB',(200,100),color).save(photo,format='PNG');photo.seek(0)
        post(f'/quality/inspection-plans/section/{identification.id}/upload_image',{'image':(photo,'same-name.png'),'description':'Vergleichsmuster '+color},expected=302)
    assert len({i.image_path for i in identification.images})==2
    dimension=next(s for s in version.sections if s.section_type=='dimension')
    drawing=Path(app.static_folder)/'drawing.png';Image.new('RGB',(600,300),'white').save(drawing)
    dimension.drawing_path='drawing.png';dimension.image_width=600;dimension.image_height=300
    dimension.characteristics[0].pos_x=100;dimension.characteristics[0].pos_y=100
    db.session.commit()
    # Update then remove a temporary row, keeping the original checks intact.
    text_section=next(s for s in version.sections if s.section_type=='text')
    post(f'/quality/inspection-plans/section/{text_section.id}/check',{'name':'Temporär','requirement':'lesbar','method':'Sichtkontrolle'})
    temporary=text_section.checks[-1]
    post(f'/quality/inspection-plans/section/{text_section.id}/check',{'check_id':temporary.id,'name':'Geändert','requirement':'vollständig lesbar','method':'Lupe'})
    assert temporary.name=='Geändert'
    post(f'/quality/inspection-plans/check/{temporary.id}/delete')
    assert len(text_section.checks)==1
    # All nine modules render; a stale form never overwrites a newer change.
    page=client.get(url());assert page.status_code==200
    stale=revision_token(version);section=version.sections[0]
    post(f'/quality/inspection-plans/section/{section.id}/move',{'direction':'down'})
    assert client.post(url(),data={'access_csrf':csrf,'revision_token':stale,'add_section_type':'text'}).status_code==409
    db.session.rollback()
    # GET and export never change workflow/audit data.
    count=QualityInspectionChangeLog.query.count()
    pdf=generate_inspection_plan_pdf(version.id)
    out=Path(__file__).resolve().parents[2]/'quality_plan_test.pdf';out.write_bytes(pdf.getvalue())
    from pypdf import PdfReader
    pdftext='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf.getvalue())).pages)
    assert all(meta[0] in pdftext for meta in MODULES.values())
    assert 'Vergleichsmuster red' in pdftext and 'Vergleichsmuster blue' in pdftext
    assert client.get('/quality/inspection-plans/inspectionplan').status_code==200
    response=client.get('/quality/inspection-plans/export_pdf/'+str(version.id));assert response.status_code==200 and response.data.startswith(b'%PDF')
    assert QualityInspectionChangeLog.query.count()==count and version.status=='draft'
    # Review locks every mutation route, including old marker paths.
    post(url(),{'workflow_action':'review'});assert version.status=='review'
    post(f'/quality/inspection-plans/section/{section.id}/settings',{},expected=409);db.session.rollback()
    post(url(),{'workflow_action':'return'});assert version.status=='draft'
    post(url(),{'workflow_action':'review'});post(url(),{'workflow_action':'release'});assert version.status=='released' and version.released_by_id==user.id
    dimension=next(s for s in version.sections if s.section_type=='dimension')
    marker=client.post('/quality/inspection-plans/add_point',json={'section_id':dimension.id,'pos_x':20,'pos_y':20},headers={'X-Access-CSRF':csrf,'X-QM-Revision':revision_token(version)})
    assert marker.status_code==409;db.session.rollback()
    post(url(),{'workflow_action':'close'});assert version.status=='closed'
    counts=[len(s.checks) for s in version.sections]
    post(f'/quality/inspection-plans/{version.id}/new_revision')
    new=QualityInspectionPlanVersion.query.order_by(QualityInspectionPlanVersion.id.desc()).first()
    assert new.id!=version.id and new.status=='draft' and new.revision=='1.1'
    assert [len(s.checks) for s in new.sections]==counts and all(s.inspection_settings for s in new.sections)
    assert len(next(s for s in new.sections if s.section_type=='identification').images)==2
    assert next(s for s in new.sections if s.section_type=='dimension').image_width==600
    assert version.status=='closed'
    post(url(),{'workflow_action':'review'},expected=409);db.session.rollback()
    assert QualityInspectionChangeLog.query.filter_by(version_id=new.id,user_id=user.id).count()>0
    assert client.get(f'/quality/inspection-plans/999999/version/{new.id}/edit').status_code==404
    # Save HTML for isolated mobile layout checks without live credentials/data.
    html=client.get(url(new)).get_data(as_text=True)
    (Path(__file__).resolve().parents[2]/'quality_plan_test.html').write_text(html)
    # View permission does not grant editing, release, deletion or export.
    from factoryos.models.user import User
    from factoryos.modules.admin.roles.models import Role
    from factoryos.modules.admin.permissions.models import Permission
    permission=Permission.query.filter_by(name='quality.view').first()
    if not permission:permission=Permission(name='quality.view');db.session.add(permission)
    reader=User(username='quality-reader',password_hash='unused',active=True,role=Role(name='quality-reader',active=True,permissions=[permission]));db.session.add(reader);db.session.commit()
    restricted=app.test_client()
    with restricted.session_transaction() as session:session['_user_id']=str(reader.id);session['_fresh']=True
    assert restricted.get(url(new)).status_code==200
    assert restricted.post(url(new),data={'workflow_action':'review'}).status_code==403
    assert restricted.get('/quality/inspection-plans/export_pdf/'+str(new.id)).status_code==403
print('PASS: additive upgrade twice; nine modules; field validation/preserved input; workflow; revision cloning; frozen legacy routes; stale edit/CSRF guards; PDF completeness/no GET writes; plan binding and audit actor.')
