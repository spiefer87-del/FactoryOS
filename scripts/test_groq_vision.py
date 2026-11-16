"""No real provider calls or credentials; isolated SQLite and fake HTTP."""
import copy
import io
import json
import os
import runpy
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_setup_reports.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.setup_reports import external_vision as vision
from factoryos.modules.setup_reports.models import SetupReport,SetupReportPhoto
from factoryos.modules.setup_reports.service import clean_data
from factoryos.modules.masterdata.materials.services.material_scan_service import ScanUnavailable,ScanBusy


def reading(field,value,unit,kind='setting'):
    return dict(field=field,value=value,unit=unit,kind=kind,evidence='visible row / column')


sample=dict(page='injection',readings=[reading('dosing_position','130.00','cm³'),
    reading('back_pressure','150','bar_spez'),reading('cycle_target','119.92','s','measured'),
    reading('dosing_time','14.436','s','measured'),reading('operator','secret','')],
    profiles=[dict(profile='holding_profile',rows=[dict(label='1',active='yes',values=dict(
        pressure=reading('', '220','bar_spez'),time=reading('','8.000','s')))])])
result=vision.validate_result(sample,'injection')
assert {p['field'] for p in result['proposals']}=={'dosing_position','back_pressure','dosing_time'}
assert result['profiles']['holding_profile']['rows'][0]['active']=='unknown'
assert all(p['status']=='open' for p in result['proposals'])
for bad in ('00','0','0.0','NaN','1e99','130O','-2'):
    assert not vision.validate_result(dict(page='injection',readings=[reading('dosing_position',bad,'cm³')]),'injection')['proposals']
assert not vision.validate_result(dict(page='statistics',readings=sample['readings']),'injection')['proposals']
assert not vision.validate_result(dict(page='injection',readings=[reading('dosing_position','130','bar')]),'injection')['proposals']
assert not vision.validate_result(dict(page='injection',readings=sample['readings']),'movement')['proposals']
duplicate=dict(page='injection',readings=[reading('dosing_position',v,'cm³') for v in ('130','140','150')])
assert not vision.validate_result(duplicate,'injection')['proposals']
temps=vision.validate_result(dict(page='temperature',profiles=[dict(profile='cylinder',rows=[
    dict(label='EF',values={'actual':reading('','66','°C','measured'),'set':reading('','65','°C')})])]),'temperature')
assert temps['profiles']['cylinder']['rows'][0]['values']['set']['value']=='65'
assert temps['profiles']['cylinder']['rows'][0]['values']['actual']['value']=='66'
assert temps['profiles']['cylinder']['rows'][0]['values']['plus']['value']==''

class Response:
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,size):return self.body[:size]


key='test-not-a-real-secret-0123456789'
env=dict(GROQ_API_KEY=key,FACTORYOS_GROQ_ENABLED='1',FACTORYOS_GROQ_FREE_CONFIRMED='1')
with tempfile.TemporaryDirectory(prefix='factoryos-groq-test-') as folder, patch.dict(os.environ,env), patch.object(app,'instance_path',folder), app.app_context():
    report=db.session.get(SetupReport,fixture['clone'].id)
    client=fixture['client_for'](fixture['admin'])
    url=fixture['base']+'/'+str(report.id)
    html=client.get(url).get_data(as_text=True)
    assert key not in html and 'sr-external-consent' in html
    with client.session_transaction() as session:token=session['access_csrf']
    headers={'X-Access-CSRF':token}
    raw=fixture['raw']
    def scan(**changes):
        data=dict(version=str(report.version),provider='groq',step='injection',profile='nc5',external_consent='yes',photo=(io.BytesIO(raw),'screen.jpg'))
        data.update(changes)
        response=client.post(url+'/scan',data=data,headers=headers)
        db.session.refresh(report)
        return response
    with patch.object(vision,'request_model',return_value=sample) as call:
        assert scan(external_consent='no').status_code==400
        assert scan(step='identity').status_code==400
        with patch.dict(os.environ,{'FACTORYOS_GROQ_ENABLED':'0'}):assert scan().status_code==503
        assert call.call_count==0
        before=copy.deepcopy(report.data)
        first=scan();assert first.status_code==200,first.json
        assert report.data==before and call.call_count==1
        assert first.json['result']['provider']=='groq' and key not in json.dumps(first.json)
        count=SetupReportPhoto.query.filter_by(report_id=report.id).count()
        second=scan();assert second.status_code==200 and second.json['cached'] is True
        assert second.json['photo_id']==first.json['photo_id'] and call.call_count==1
        assert SetupReportPhoto.query.filter_by(report_id=report.id).count()==count
        assert json.loads((Path(folder)/'groq_vision_usage.json').read_text())['count']==1
        # Server-side provenance survives applying/saving a profile with blank cells.
        proposed=copy.deepcopy(report.data)
        proposed['profiles']['holding_profile']={**first.json['result']['profiles']['holding_profile'],'photo_id':first.json['photo_id']}
        proposed['values']['dosing_position']={**first.json['result']['proposals'][0],'photo_id':first.json['photo_id']}
        cleaned=clean_data(report,proposed,{})
        assert cleaned['values']['dosing_position']['origin']=='photo'
        assert 'Groq' in cleaned['values']['dosing_position']['evidence']
        assert cleaned['values']['dosing_position']['status']=='open'
        assert cleaned['profiles']['holding_profile']['origin']=='photo'
        assert cleaned['profiles']['holding_profile']['status']=='open'
    # Edit right alone is insufficient for external transfer.
    editor=fixture['client_for'](fixture['editor'])
    editor.get(url)
    with editor.session_transaction() as session:etoken=session['access_csrf']
    with patch.object(vision,'request_model') as call:
        denied=editor.post(url+'/scan',data=dict(version=report.version,provider='groq',external_consent='yes'),headers={'X-Access-CSRF':etoken})
        assert denied.status_code==403 and call.call_count==0
    # Fixed endpoint, key only in Authorization, no master context in prompt.
    body=json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(sample)))])).encode()
    with patch('urllib.request.OpenerDirector.open',return_value=Response(body)) as opened:
        assert vision.request_model(b'JPEG','injection','nc5')==sample
        req=opened.call_args.args[0]
        assert req.full_url==vision.ENDPOINT and req.headers['Authorization']=='Bearer '+key
        payload=json.loads(req.data)
        assert key not in req.data.decode() and 'tools' not in payload
        assert payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')
    for code in (401,403,429,500,302):
        with patch('urllib.request.OpenerDirector.open',side_effect=urllib.error.HTTPError(vision.ENDPOINT,code,key,None,None)):
            try:vision.request_model(b'JPEG','injection','nc5');assert False
            except ScanUnavailable as error:assert key not in str(error)
    assert vision.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example') is None
    # Quota is persistent, shared, includes failures, and fails closed if damaged.
    for _ in range(9):vision.reserve_request()
    try:vision.reserve_request();assert False
    except ScanBusy:pass
    assert (Path(folder)/'groq_vision_usage.json').stat().st_mode & 0o077==0
    with patch.object(Path,'read_text',return_value='broken'):
        try:vision.reserve_request();assert False
        except ScanUnavailable:pass
print('PASS: external opt-in, permission/CSRF/version gates, bounded JSON/units, Soll/Ist, no zero repair, provenance, no automatic adoption, persistent quota, same-report cache, secret isolation, fixed HTTPS/no redirects/retries. No real API call made.')
