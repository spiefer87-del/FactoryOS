"""Legacy payloads, supplemental journals and formerly missing activity writers."""
import runpy
from pathlib import Path
from datetime import datetime, timezone
from types import SimpleNamespace
from io import BytesIO
from uuid import uuid4
from openpyxl import Workbook
from flask import render_template
from flask_login import login_user

fixture=runpy.run_path(str(Path(__file__).with_name('test_project_workspace.py')))
app=fixture['app']
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog
from factoryos.core.services.activity_presenter import present_change_logs
from factoryos.core.services.change_log_service import log_change,build_changes
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.inventory.models import WarehouseLocation,WarehouseLot,WarehouseEvent,WarehouseLine
from factoryos.modules.quality.inspection_plan.models import QualityInspectionPlan,QualityInspectionPlanVersion,QualityInspectionChangeLog
from factoryos.modules.quality.gauges.calibration_service import create_gauge,create_gauge_calibration,update_gauge_status
from factoryos.modules.admin.roles.services.role_service import create_role,update_role
from factoryos.modules.masterdata.tools.services.tool_import_service import import_tools_from_excel

with app.app_context():
    admin=db.session.merge(fixture['admin']);tool=db.session.merge(fixture['tool'])
    article=fixture['fixture']['article']
    from factoryos.modules.masterdata.articles.models import Article
    article=db.session.merge(article)
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    client=fixture['client'](admin)
    def row(changes,category='masterdata',action='update',kind='article'):
        return SimpleNamespace(id=1,entity_type=kind,entity_id=1,entity_name='TEST-ENTITY',
            category=category,action=action,changes=changes,user=admin,created_at=now)
    cases=[
        row({'deleted_defect':{'reason':'Doppelt erfasst','old':{'id':1,'article_no':'101010005','title':'Farbabweichung','description':'Farbe prüfen','remedy':'Farbbatch prüfen','archived':True,'photos':[{'id':1,'filename':'HIDDEN-RANDOM.jpg'}]},'new':None}},'article_defect','delete'),
        row({'defect_catalog':{'old':None,'new':{'entry_id':2,'title':'Farbe','archived':False,'new_photos':0}}},'article_defect','create'),
        row({'photo':{'old':{'id':2,'entry_id':2},'new':None}},'article_defect_photo','delete'),
        row({'deviation_confirmation':{'reason':'Fachlich geprüft','category':'Sonstiger Grund','snapshot':{'expected_seconds':30,'recorded_seconds':0,'percent':0,'facts':{'complete':False}}}},'production_deviation',kind='order'),
        row({'article_no':'A001','article_name':'Winkel'},action='create'),
        row({'description':{'old':None,'new':''},'built_by':{'old':'','new':None},'cavities':{'old':0,'new':2}},kind='tool'),
        row({'record':{'old':{'state':'draft','data':{'instructions':'Alt'}},'new':{'state':'review','data':{'instructions':'Neu'},'checks':{'external':{'status':'granted','date':'2026-11-17'}}}}},'orders',kind='sampling'),
        row({'planning':{'old':[],'new':[{'order_id':1,'position':1,'note':'Vorrang'}]}},'planning',kind='machine'),
        row({'booking_review':{'action':'delete','reason':'Doppelt','old':{'start_time':'2026-11-17T10:00:00','end_time':None},'new':None}},'booking_review','delete','order'),
        row({'password_changed':True,'password_hash':'HIDDEN-HASH','access_token':'HIDDEN-TOKEN','description':'<script>alert(1)</script>'},kind='user'),
        row({'has_conversion_kit':{'old':True,'new':False},'cycle_time_s':{'old':None,'new':30.92}},kind='tool'),
    ]
    with app.test_request_context('/activity/?limit=all'):
        login_user(admin)
        views=present_change_logs(cases)
        assert views[0].action_label=='Fehlereintrag gelöscht'
        assert views[2].action_label=='Foto aus Fehlerkatalog entfernt'
        assert views[3].action_label=='Produktionsabweichung bestätigt'
        assert views[8].action_label=='Zeitbuchung gelöscht'
        html=render_template('components/changelog.html',logs=cases)
        assert 'HIDDEN-' not in html and '&lt;script&gt;' in html and '<script>alert' not in html
        for raw in ('deleted_defect','defect_catalog','deviation_confirmation','built_by',"{'",'→ -'):
            assert raw not in html,raw
        assert '30,92' in html and 'Nein' in html and 'Freigabe erteilt' in html
        assert not any(line['label'] in ('Beschreibung','Werkzeugbauer / Hersteller') for line in views[5].lines)
        assert any(line['old']=='0' and line['value']=='2' for line in views[5].lines)
        assert any(line['value']=='0' for line in views[3].lines)
        assert build_changes(SimpleNamespace(description=None),{'description':''},['description'])=={}

    # Existing journals, not newly invented copies, appear in the main feed.
    place=WarehouseLocation(code='ACTIVITY-A1',description='Testlager')
    lot=WarehouseLot(article_id=article.id,article_no=article.article_no,article_name='Artikelname',batch='ACTIVITY-LOT',quantity=12,origin='opening')
    plan=QualityInspectionPlan(article_id=article.id,tool_id=tool.id,created_by_id=admin.id)
    db.session.add_all([place,lot,plan]);db.session.flush()
    version=QualityInspectionPlanVersion(plan_id=plan.id,revision='1.0',status='draft');db.session.add(version);db.session.flush()
    quality=QualityInspectionChangeLog(plan_id=plan.id,version_id=version.id,action='CREATE_PLAN',message='ACTIVITY-QM-NOTE',user_id=admin.id)
    event=WarehouseEvent(command_id=str(uuid4()),payload_hash='0'*64,kind='opening',lot_id=lot.id,quantity=12,reason='ACTIVITY-WAREHOUSE-NOTE',user_id=admin.id,details={'destination_id':str(place.id)})
    db.session.add_all([quality,event]);db.session.flush()
    db.session.add(WarehouseLine(event_id=event.id,lot_id=lot.id,location_id=place.id,status='blocked',quantity=12));db.session.commit()
    counts=(ChangeLog.query.count(),WarehouseEvent.query.count(),QualityInspectionChangeLog.query.count())
    for _ in range(2):
        html=client.get('/activity/?limit=all').get_data(as_text=True)
        assert html.count('ACTIVITY-QM-NOTE')==1 and html.count('ACTIVITY-WAREHOUSE-NOTE')==1
        assert 'ACTIVITY-LOT' in html and 'ACTIVITY-A1' in html
    assert counts==(ChangeLog.query.count(),WarehouseEvent.query.count(),QualityInspectionChangeLog.query.count())
    assert 'ACTIVITY-QM-NOTE' not in client.get('/activity/?type=inventory&limit=all').get_data(as_text=True)
    assert 'ACTIVITY-WAREHOUSE-NOTE' not in client.get('/activity/?type=qm_plan&limit=all').get_data(as_text=True)

    # New operations audit in the same transaction, without credentials or hashes.
    with app.test_request_context():
        login_user(admin)
        gauge=create_gauge({'gauge_no':'ACTIVITY-GAUGE','name':'Messschieber','calibration_interval':'12'})
        update_gauge_status(gauge.id,'inspection')
        create_gauge_calibration(gauge.id,{'calibration_date':'2026-11-17','result':'ok','certificate_no':'ACTIVITY-CERT'})
        assert ChangeLog.query.filter_by(entity_type='gauge',entity_id=gauge.id).count()==3
        from factoryos.modules.quality.gauges.models import GaugeCalibration
        from datetime import date
        db.session.add(GaugeCalibration(gauge_id=gauge.id,calibration_date=date(2025,11,17),result='ok',certificate_no='HISTORICAL-CERT'))
        db.session.commit()
        role=create_role('activity-created-role','Neue Rolle')
        update_role(role,'activity-renamed-role','Geändert',True)
        assert ChangeLog.query.filter_by(entity_type='role',entity_id=role.id).count()==2
        before_count=ChangeLog.query.count()
        log_change('article',article.id,'update',{'description':{'old':'Alt','new':'ROLLBACK-MARKER'}})
        db.session.rollback()
        assert ChangeLog.query.count()==before_count
        workbook=Workbook();sheet=workbook.active
        sheet.append(['Werkzeugnummer','Bezeichnung']);sheet.append(['ACTIVITY-IMPORT','Importiert'])
        file=BytesIO();workbook.save(file);file.seek(0)
        result=import_tools_from_excel(file)
        assert result['created']==1,result
        assert ChangeLog.query.filter_by(entity_type='tool',entity_name='ACTIVITY-IMPORT',action='import').count()==1
    before_count=ChangeLog.query.count()
    response=client.post('/admin/users/create',data={'access_csrf':'project-test','username':'activity-user','password':'NOT-IN-AUDIT-password','role_id':admin.role_id})
    assert response.status_code==302,response.get_data(as_text=True)
    assert ChangeLog.query.count()==before_count+1
    saved=ChangeLog.query.order_by(ChangeLog.id.desc()).first()
    assert saved.entity_type=='user' and 'NOT-IN-AUDIT' not in str(saved.changes) and 'password_hash' not in str(saved.changes)
    # Successful file operations and deletions have their own audit events.
    response=client.post(f'/masterdata/tools/{tool.id}/documents/upload',data={
        'access_csrf':'project-test','document_category':'documents','documents':(BytesIO(b'%PDF-1.4 test'),'activity-document.pdf')})
    assert response.status_code==302
    assert ChangeLog.query.filter_by(entity_type='tool',entity_id=tool.id,action='document_add').count()==1
    response=client.post(f'/masterdata/tools/{tool.id}/documents/documents/activity-document.pdf/delete',data={'access_csrf':'project-test'})
    assert response.status_code==302
    assert ChangeLog.query.filter_by(entity_type='tool',entity_id=tool.id,action='document_delete').count()==1
    from factoryos.modules.orders.models import Order
    disposable=Order(order_no='ACTIVITY-DELETE',status='offen',is_project=False)
    db.session.add(disposable);db.session.commit();disposable_id=disposable.id
    response=client.post(f'/orders/delete/{disposable_id}',data={'access_csrf':'project-test'})
    assert response.status_code==302 and db.session.get(Order,disposable_id) is None
    assert ChangeLog.query.filter_by(entity_type='order',entity_id=disposable_id,action='delete').count()==1
    with app.test_request_context():
        login_user(admin)
        from factoryos.modules.production.services.calendar_service import get_or_create_calendar_settings,update_calendar_settings,create_calendar_exception,delete_calendar_exception
        settings=get_or_create_calendar_settings()
        update_calendar_settings(settings,{'week_start_day':'0','week_start_time':'07:00','week_end_day':'4','week_end_time':'21:00'})
        exception=create_calendar_exception({'title':'ACTIVITY-HOLIDAY','start_date':'2026-12-24','end_date':'2026-12-24','all_day':'yes'},admin.id)
        assert delete_calendar_exception(exception.id)
        assert ChangeLog.query.filter_by(entity_type='calendar').count()==3
    calibrations=client.get('/activity/?type=gauge&limit=all').get_data(as_text=True)
    assert calibrations.count('ACTIVITY-CERT')==1 and calibrations.count('HISTORICAL-CERT')==1
    assert 'Nicht protokolliert (älterer Kalibriereintrag)' in calibrations
    # Source permissions are required even with access to the main activity page.
    permission=Permission(name='activity.view',description='Aktivitäten ansehen');db.session.add(permission)
    role=Role(name='activity-reader-review',active=True,permissions=[permission])
    reader=User(username='activity-reader-review',password_hash='unused',active=True,role=role)
    db.session.add_all([role,reader]);db.session.commit()
    reader_html=fixture['client'](reader).get('/activity/?limit=all').get_data(as_text=True)
    assert 'ACTIVITY-QM-NOTE' not in reader_html and 'ACTIVITY-WAREHOUSE-NOTE' not in reader_html
    assert 'ACTIVITY-CERT' not in reader_html and 'HISTORICAL-CERT' not in reader_html
    print('PASS: screenshot regressions, scalars/nesting/zero/false/empty values, dates, escaped text and hidden secrets, category-specific headings, historical QM/warehouse journals once, source permissions, gauge/role/user/import auditing, transaction rollback')
