"""Isolated SQLite workflow + local OCR regressions; never production data."""
import copy
import io
import re
import runpy
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.machines.models import Machine
from factoryos.modules.setup_reports.models import SetupReport,SetupReportRevision,SetupReportPhoto
from factoryos.modules.setup_reports.service import gaps,clean_data
from factoryos.modules.setup_reports.ocr import parse_words,read_screen
from factoryos.modules.setup_reports.schema import FIELDS,PROFILES
from scripts.upgrade_setup_reports import run_upgrade


def words_fixture():
    words=[]
    def w(text,x,y,line,blue=False):words.append(dict(text=text,x=x,y=y,w=35,h=14,line=line,confidence=95,blue=blue))
    w('TEMPERATUREN',400,20,1)
    for i,(label,set_,actual) in enumerate((('DH1','285','285'),('MH3','290','290'),('MH2','285','285'),('MH1','280','280'),('EF','65','66'))):
        x=250+i*130;w(label,x,210,2);w(actual,x,250,3,True);w(set_,x,290,4)
    w('Ist',90,250,3);w('Soll',90,290,4)
    return words

result=parse_words(words_fixture(),'nc5');rows=result['profiles']['cylinder']['rows']
assert next(r for r in rows if r['label']=='EF')['values']['set']['value']=='65'
assert next(r for r in rows if r['label']=='EF')['values']['actual']['value']=='66'
assert all(r['active']=='unknown' for r in rows)
assert not parse_words(words_fixture(),'unknown')['profiles']
assert not parse_words([dict(text='PDE STATISTIK',x=0,y=0,w=100,h=14,line=1,confidence=95)],'nc5')['proposals']
damaged=words_fixture();damaged=[w for w in damaged if w['text']!='Soll']
assert not parse_words(damaged,'nc5')['profiles']

with app.app_context():
    for model in (SetupReportPhoto,SetupReportRevision,SetupReport):model.__table__.drop(db.engine,checkfirst=True)
    before=Tool.query.count();run_upgrade(True);run_upgrade();run_upgrade();assert Tool.query.count()==before
    assert Permission.query.filter(Permission.name.like('setup_reports.%')).count()==6
    tool=Tool.query.filter_by(tool_no='W001').one();article=Article.query.filter_by(article_no='A001').one()
    material=Material.query.filter_by(material_no='R001').one();machine=Machine.query.filter_by(machine_no='M001').one()
    article.tools=[tool];article.material=material;article.cycle_time_s=42;article.shot_weight_g=50
    material.manufacturer='Example Polymers';material.drying_temperature_c=80;material.drying_time_h=4
    machine.controller_type='NC5';db.session.commit()
    admin=User.query.filter_by(username='test').one()
    def client_for(user):
        c=app.test_client()
        with c.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
        return c
    client=client_for(admin);base=f'/masterdata/tools/{tool.id}/setup-reports'
    assert client.get(base+'/').status_code==200
    assert 'Einstellberichte / Wizard' in client.get(f'/masterdata/tools/{tool.id}').get_data(as_text=True)
    with client.session_transaction() as s:token=s['access_csrf']
    headers={'X-Access-CSRF':token}
    assert client.post(base+'/new').status_code==400
    response=client.post(base+'/new',data={'access_csrf':token});assert response.status_code==302
    report=SetupReport.query.one();url=base+'/'+str(report.id)
    page=client.get(url);assert page.status_code==200,page.get_data(as_text=True)
    html=page.get_data(as_text=True);assert 'Manuell eingeben' in html and 'Foto-Erkennung versuchen' in html
    assert 'Geprüft abschließen' in html and 'sr-context-confirm' in html
    ids=dict(machine_id=machine.id,article_id=article.id)
    response=client.post(url+'/context',json={'ids':ids},headers=headers);assert response.status_code==200,response.json
    context=response.json['context'];suggestions=response.json['values'];context_preview_token=response.json['context_token']
    assert suggestions['drying_temperature']['origin']=='recommendation' and suggestions['drying_temperature']['status']=='open'
    assert suggestions['cycle_target']['value']=='42.0'
    assert report.context.get('machine_id') is None # proposal endpoint never saves.
    payload=dict(version=report.version,ids=context,context_token=context_preview_token,data=copy.deepcopy(report.data))
    payload['data']['values'].update(suggestions)
    assert client.post(url+'/save',json=payload).status_code==400
    wrong_preview=copy.deepcopy(payload);wrong_preview['context_token']='tampered'
    assert client.post(url+'/save',json=wrong_preview,headers=headers).status_code==400
    assert client.post(url+'/save',json={**payload,'release':True},headers=headers).status_code==422
    response=client.post(url+'/save',json=payload,headers=headers);assert response.status_code==200,response.json
    assert response.json['version']>payload['version'] and SetupReportRevision.query.count()==2
    assert client.post(url+'/save',json=payload,headers=headers).status_code==409
    payload.update(version=response.json['version'],data=response.json['data'])
    bad=copy.deepcopy(payload);bad['data']['values']['cycle_target']['value']='NaN'
    assert client.post(url+'/save',json=bad,headers=headers).status_code==400
    bad=copy.deepcopy(payload);bad['data']['values']['cycle_target']['value']='0'
    assert client.post(url+'/save',json=bad,headers=headers).status_code==400
    # A photo result is held for explicit selection. It never changes report parameters.
    image=Image.new('RGB',(1200,400),'white');draw=ImageDraw.Draw(image)
    draw.text((60,40),'TEMPERATUREN',font=ImageFont.truetype('DejaVuSans.ttf',40),fill='black')
    stream=io.BytesIO();image.save(stream,'JPEG');raw=stream.getvalue()
    previous=copy.deepcopy(report.data)
    with patch('factoryos.modules.setup_reports.ocr.read_screen',return_value=(raw,result)):
        response=client.post(url+'/scan',data=dict(version=report.version,profile='nc5',photo=(io.BytesIO(raw),'screen.jpg')),headers=headers)
    assert response.status_code==200,response.json
    photo_id=response.json['photo_id'];assert report.data==previous
    photo_url=response.json['url'];assert client.get(photo_url).status_code==200
    assert client.get(photo_url).headers['Cache-Control']=='private, no-store'
    payload['version']=report.version
    payload['data']['profiles']['cylinder']={**result['profiles']['cylinder'],'photo_id':photo_id}
    # Deliberately mark complete only after activity and every actual setting were checked.
    profile=payload['data']['profiles']['cylinder'];profile['status']='confirmed'
    for row in profile['rows']:row['active']='yes'
    payload['data']['context_confirmed']=True
    for key,spec in FIELDS.items():
        item=payload['data']['values'].setdefault(key,dict(value='',unit=spec['unit'],origin='manual'))
        item.update(status='confirmed' if item['value'] else 'na',reason='' if item['value'] else 'Im Test nicht verwendet')
    for key in PROFILES:
        if key!='cylinder':payload['data']['profiles'][key]=dict(rows=[],status='na',reason='Im Test nicht vorhanden')
    response=client.post(url+'/save',json=payload,headers=headers);assert response.status_code==200,response.json
    payload.update(version=report.version,data=response.json['data'])
    assert not gaps(report),gaps(report)
    # Confirming activity preserves the image evidence for unchanged OCR cells.
    assert report.data['profiles']['cylinder']['origin']=='photo'
    response=client.get(url+'/pdf');assert response.status_code==200 and response.data.startswith(b'%PDF')
    (ROOT.parent/'setup_report_test.pdf').write_bytes(response.data)
    response=client.post(url+'/save',json={**payload,'release':True},headers=headers);assert response.status_code==200,response.json
    assert report.state=='released'
    assert client.post(url+'/save',json={**payload,'version':report.version},headers=headers).status_code==409
    assert client.post(url+'/scan',data=dict(version=report.version),headers=headers).status_code==409
    # Read-only history, old data retained, cloning resets every confirmation.
    assert client.get(url+'/history/1').status_code==200
    assert client.post(base+'/new',data=dict(access_csrf=token,previous_id=report.id)).status_code==302
    clone=SetupReport.query.order_by(SetupReport.id.desc()).first()
    assert clone.tool_id==tool.id and clone.previous_id==report.id
    assert not clone.data['context_confirmed'] and all(v['status']=='open' for v in clone.data['values'].values())
    other=Tool(tool_no='OTHER');db.session.add(other);db.session.commit()
    assert client.get(f'/masterdata/tools/{other.id}/setup-reports/{report.id}').status_code==404
    assert client.get(f'/masterdata/tools/{other.id}/setup-reports/{report.id}/photos/{photo_id}').status_code==404
    reader=User(username='setup-reader',password_hash='unused',active=True,role=Role(name='setup-reader',active=True,permissions=[Permission.query.filter_by(name='setup_reports.view').one()]))
    db.session.add(reader)
    editor=User(username='setup-editor',password_hash='unused',active=True,role=Role(name='setup-editor',active=True,permissions=[Permission.query.filter_by(name='setup_reports.view').one(),Permission.query.filter_by(name='setup_reports.edit').one()]))
    db.session.add_all([reader,editor]);db.session.commit()
    c=client_for(reader);assert c.get(url).status_code==200
    assert 'Geprüft abschließen' not in c.get(url).get_data(as_text=True)
    assert c.post(base+'/new',data=dict(access_csrf=token)).status_code==403
    assert c.post(url+'/save',json=payload,headers=headers).status_code==403
    assert c.get(url+'/pdf').status_code==403
    clone_url=base+'/'+str(clone.id)
    editor_client=client_for(editor);assert editor_client.get(clone_url).status_code==200
    with editor_client.session_transaction() as s:editor_token=s['access_csrf']
    assert editor_client.post(clone_url+'/save',json={'version':clone.version,'release':True},headers={'X-Access-CSRF':editor_token}).status_code==403
    assert app.test_client().get(photo_url).status_code==302
    assert client.post(f'/masterdata/tools/delete/{tool.id}',data=dict(access_csrf=token)).status_code==302
    assert db.session.get(Tool,tool.id)
    # Actual Tesseract execution on a generated label, separate from parser fixtures.
    binary,recognized=read_screen(raw,'nc5');assert binary.startswith(b'\xff\xd8') and 'TEMPERAT' in recognized['text'].upper()
print('PASS: wizard/manual draft, unconfirmed master recommendations, strict release, optimistic locks, read-only history, cloning, photo isolation/no overwrite, permissions/CSRF, no master writes, PDF, conservative NC5 Soll/Ist and real local OCR.')

if '--photos' in __import__('sys').argv:
    with app.app_context():
        for name in __import__('sys').argv[__import__('sys').argv.index('--photos')+1:]:
            _,read=read_screen(Path(name).read_bytes(),'nc5')
            print(Path(name).name,read['page'],read['proposals'],read['profiles'],read['notes'])

if __import__('os').environ.get('SETUP_REPORT_TEST_SERVER')=='1':
    def test_login_only():
        from flask import session,redirect,request
        if request.path=='/__test_login':
            session['_user_id']=str(admin.id);session['_fresh']=True
            return redirect(clone_url)
    app.before_request_funcs[None].insert(0,test_login_only)
    app.run(host='127.0.0.1',port=8765,debug=False,use_reloader=False,threaded=False)
