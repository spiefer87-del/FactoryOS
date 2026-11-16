"""Field-addressed validation and R-radius regression; isolated DB only."""
import copy
import json
import re
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_setup_reports.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.setup_reports.models import SetupReport,SetupReportRevision
from factoryos.modules.setup_reports.service import numeric,clean_data
from factoryos.modules.setup_reports.validation import ReportValidationError

for raw,expected in [('R40','40'),('R 40','40'),('r 40,5','40.5'),('40','40'),('40,5','40.5')]:
    assert numeric(raw,field='nozzle_radius')==expected
for key,value in [('nozzle_radius','R40/50'),('nozzle_radius','R'),('nozzle_radius','R40 mm'),('cycle_target','R40')]:
    try:numeric(value,field=key);assert False
    except ReportValidationError as error:
        assert error.errors[0]['field']==key and error.errors[0]['message']

with app.app_context():
    report=db.session.get(SetupReport,fixture['clone'].id)
    client=fixture['client_for'](fixture['admin']);url=fixture['base']+'/'+str(report.id)
    html=client.get(url).get_data(as_text=True)
    assert 'id="sr-errors"' in html and 'field-errors' in html
    boot=json.loads(re.search(r'<script id="sr-boot" type="application/json">(.*?)</script>',html,re.S).group(1))
    with client.session_transaction() as session:token=session['access_csrf']
    headers={'X-Access-CSRF':token}
    def save(data):
        response=client.post(url+'/save',json=dict(version=report.version,ids=report.context,context_token=boot['context_token'],data=data),headers=headers)
        db.session.refresh(report)
        return response
    previous=copy.deepcopy(report.data);version=report.version;revisions=SetupReportRevision.query.count()
    data=copy.deepcopy(previous);data['values']['nozzle_radius'].update(value='R40/50',status='open')
    response=save(data);assert response.status_code==400,response.json
    issue=response.json['errors'][0]
    assert issue['field']=='nozzle_radius' and issue['step']=='identity' and 'Düsenradius' in issue['label']
    assert report.data==previous and report.version==version and SetupReportRevision.query.count()==revisions
    data['values']['nozzle_radius']['value']='R 40,5'
    response=save(data);assert response.status_code==200,response.json
    assert report.data['values']['nozzle_radius']['value']=='40.5'
    assert report.data['values']['nozzle_radius']['unit']=='mm'
    data=copy.deepcopy(report.data)
    data['profiles']['injection_profile']=dict(status='open',rows=[dict(label='1',active='yes',values={'position':dict(value='130/140',unit='cm³')})])
    response=save(data);assert response.status_code==400,response.json
    issue=response.json['errors'][0]
    assert issue['profile']=='injection_profile' and issue['row']==0 and issue['column']=='position'
    assert issue['step']=='injection' and 'Zeile 1' in issue['label'] and 'Weg / Position' in issue['label']
    data=copy.deepcopy(report.data)
    data['profiles']['cylinder']=dict(status='confirmed',rows=[dict(label='EF',active='yes',values={'actual':dict(value='66',unit='°C')})])
    response=save(data);assert response.status_code==400,response.json
    issue=response.json['errors'][0]
    assert issue['profile']=='cylinder' and issue['row']==0 and issue['column']=='set' and issue['step']=='temperature'
    data=copy.deepcopy(report.data);data['values']['operator'].update(status='na',reason='')
    response=save(data);assert response.status_code==400,response.json
    assert response.json['errors'][0]['field']=='operator' and response.json['errors'][0]['column']=='reason'
    response=client.post(url+'/context',json={'ids':{'machine_id':'not-an-id'}},headers=headers)
    assert response.status_code==400 and response.json['errors'][0]['context']=='machine_id'
print('PASS: R40/R 40/r40,5 accepted only for nozzle radius, stored numerically in mm; exact field/step/profile row/column/status/context errors; invalid saves leave DB/version/history untouched.')
