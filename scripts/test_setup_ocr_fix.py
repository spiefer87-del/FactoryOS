"""Regression: detached '00', ambiguous cells and actual adoption persistence."""
import copy
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_setup_reports.py'))
from factoryos.modules.setup_reports.ocr import parse_words,reconcile_passes
from factoryos.modules.setup_reports.screen_numbers import screen_number,safe_scalar
from factoryos.modules.setup_reports.models import SetupReport,SetupReportPhoto
from factoryos.modules.setup_reports.service import clean_data
from factoryos.extensions import db
from flask_login import login_user


def process_words(value='130.00',split=False,low_prefix=False,blue=False):
    words=[]
    def w(text,x,y,width=70,confidence=95,blue=False):
        words.append(dict(text=text,x=x,y=y,w=width,h=20,line=y,confidence=confidence,blue=blue))
    w('PROZESSOPTIMIERUNG',400,10,200)
    w('Dosieren',600,80,100)
    w('Position',100,140);w('Position',100,400)
    w('Druck',100,180);w('Druck',100,440)
    w('150',620,180,50)
    if split:
        w('130.',540,140,60,confidence=25 if low_prefix else 95)
        w('00',635,140,35)
    else:w(value,600,140,80,blue=blue)
    return words


def vals(result):return {p['field']:p['value'] for p in result['proposals']}
for raw in ('00','000','001','00.','130.','130 00','O0','0O','1e3'):
    assert screen_number(raw) is None,raw
for raw in ('0','0.0','0,00','-1','00'):
    assert not safe_scalar('dosing_position',raw),raw
assert safe_scalar('dosing_position','130,00')
assert safe_scalar('pause_time','0') # Do not ban valid zero values globally.
valid=parse_words(process_words(),'nc5')
assert vals(valid)['dosing_position']=='130.00'
for settings in ({'split':True},{'split':True,'low_prefix':True},{'value':'00'},{'value':'0.00'},{'blue':True}):
    assert 'dosing_position' not in vals(parse_words(process_words(**settings),'nc5')),settings
agreed=reconcile_passes([valid,parse_words(process_words('130,00'),'nc5')])
assert vals(agreed)['dosing_position']=='130.00'
assert 'dosing_position' not in vals(reconcile_passes([valid,parse_words(process_words('130.50'),'nc5')]))
assert not reconcile_passes([valid])['proposals']
assert not reconcile_passes([valid,dict(page='statistics',text='PDE STATISTIK',profiles={},proposals=[],notes=[])])['proposals']
assert 'dosing_position' not in vals(reconcile_passes([valid,parse_words(process_words(split=True),'nc5')]))

app=fixture['app']
with app.app_context(),app.test_request_context():
    login_user(fixture['admin'])
    report=SetupReport.query.filter_by(state='draft').first()
    photo=SetupReportPhoto(report_id=report.id,actor_id=fixture['admin'].id,image=b'fake',text='old scan',result={'proposals':[dict(field='dosing_position',value='00',unit='cm³')]})
    db.session.add(photo);db.session.commit()
    payload=copy.deepcopy(report.data)
    payload['values']['dosing_position']=dict(value='00',unit='cm³',status='open',origin='photo',photo_id=photo.id,reason='')
    try:clean_data(report,payload,{})
    except ValueError as error:assert 'unsicherer Foto-Wert' in str(error)
    else:raise AssertionError('Old stored 00 photo proposal accepted')
    # Manual correction remains possible without rewriting old photo history.
    payload['values']['dosing_position'].update(value='130.00',origin='manual',photo_id=None)
    cleaned=clean_data(report,payload,{})
    assert cleaned['values']['dosing_position']['value']=='130.00'
    assert photo.result['proposals'][0]['value']=='00'
with app.app_context():
    client=app.test_client()
    with client.session_transaction() as session:session['_user_id']=str(fixture['admin'].id);session['_fresh']=True
    page=client.get('/masterdata/setup-reports/start');assert page.status_code==200
    assert 'Werkzeugnummer' in page.get_data(as_text=True)
    assert 'Einstellbericht starten' in client.get('/masterdata/tools/').get_data(as_text=True)
    with client.session_transaction() as session:token=session['access_csrf']
    count=SetupReport.query.count()
    assert client.post('/masterdata/setup-reports/start',data={'tool_no':fixture['tool'].tool_no}).status_code==400
    assert SetupReport.query.count()==count
    assert client.post('/masterdata/setup-reports/start',data={'access_csrf':token,'tool_no':'DOES-NOT-EXIST'}).status_code==302
    assert SetupReport.query.count()==count
    response=client.post('/masterdata/setup-reports/start',data={'access_csrf':token,'tool_no':fixture['tool'].tool_no})
    assert response.status_code==302 and '/setup-reports/' in response.location
    assert SetupReport.query.count()==count+1
    assert SetupReport.query.order_by(SetupReport.id.desc()).first().tool_id==fixture['tool'].id
    reader=app.test_client()
    with reader.session_transaction() as session:session['_user_id']=str(fixture['reader'].id);session['_fresh']=True
    assert reader.get('/masterdata/setup-reports/start').status_code==403
print('PASS: numeric fragments and zero dosing rejected, blue telemetry excluded, full-cell ambiguity and low-confidence prefix rejected, two-pass agreement required, old unsafe photo proposal blocked, manual correction retained.')
print('PASS: direct dashboard tile, tool selection, CSRF, invalid tool creates no report, correct tool ownership and creation-right checks.')
