"""Standard cylinder structure, preservation and tool-addressed PDF names."""
import copy
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
fixture=runpy.run_path(str(ROOT/'scripts/test_setup_reports.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.setup_reports.models import SetupReport
from factoryos.modules.setup_reports.schema import profile_defaults,CYLINDER_ZONE_LABELS
from factoryos.modules.setup_reports.service import clean_data
from factoryos.modules.setup_reports.pdf_service import download_name
from factoryos.modules.setup_reports import pdf_service

a=profile_defaults();b=profile_defaults()
assert [r['label'] for r in a['cylinder']['rows']]==['DH','MH 3','MH 2','MH 1','Einzug']
assert all(r['active']=='yes' for r in a['cylinder']['rows'])
assert a['cylinder']['status']=='open'
assert all(c['value']=='' and c['unit']=='°C' for r in a['cylinder']['rows'] for c in r['values'].values())
a['cylinder']['rows'][0]['values']['set']['value']='220'
assert b['cylinder']['rows'][0]['values']['set']['value']==''
for number in ('COR249','6341 / FRM002','WZ Ä\\B\r\n.pdf','../../'):
    mock=SimpleNamespace(context={'tool_no':number},tool=SimpleNamespace(tool_no='CURRENT'),tool_id=52,id=7,version=3)
    name=download_name(mock)
    assert name.endswith('_Einstellbericht_7_Stand_3.pdf')
    assert not any(c in name for c in ('/','\\','\r','\n')) and not name.startswith('.')
assert download_name(SimpleNamespace(context={'tool_no':'COR249'},tool=None,tool_id=52,id=7,version=3))=='COR249_Einstellbericht_7_Stand_3.pdf'

with app.app_context():
    client=fixture['client'];base=fixture['base']
    source=db.session.get(SetupReport,fixture['report'].id)
    previous=copy.deepcopy(source.data);source_version=source.version
    with client.session_transaction() as session:token=session['access_csrf']
    response=client.post(base+'/new',data={'access_csrf':token});assert response.status_code==302
    fresh=SetupReport.query.order_by(SetupReport.id.desc()).first()
    assert fresh.data['profiles']['cylinder']==profile_defaults()['cylinder']
    # Values, extra zones and order survive validation/saving; no reapplication of template.
    payload=copy.deepcopy(fresh.data);profile=payload['profiles']['cylinder']
    profile['rows'][0]['values']['set']['value']='220'
    profile['rows'][0],profile['rows'][1]=profile['rows'][1],profile['rows'][0]
    extra=copy.deepcopy(profile['rows'][0]);extra['label']='MH 4';extra['values']['set']['value']='215'
    profile['rows'].append(extra);profile['rows'].pop(2)
    cleaned=clean_data(fresh,payload,{})
    assert [r['label'] for r in cleaned['profiles']['cylinder']['rows']]==['MH 3','DH','MH 1','Einzug','MH 4']
    assert cleaned['profiles']['cylinder']['rows'][1]['values']['set']['value']=='220'
    fresh.data=cleaned;db.session.commit()
    client.get(response.location);db.session.refresh(fresh)
    assert fresh.data==cleaned
    # Legacy empty and read-only reports are not populated by merely opening them.
    client.get(base+'/'+str(source.id));db.session.refresh(source)
    assert source.data==previous and source.version==source_version
    payload=copy.deepcopy(fresh.data);payload['profiles']['cylinder']['rows']=[]
    fresh.data=clean_data(fresh,payload,{});db.session.commit()
    client.get(base+'/'+str(fresh.id));db.session.refresh(fresh)
    assert fresh.data['profiles']['cylinder']['rows']==[]
    with patch.object(pdf_service,'BaseDocTemplate',wraps=pdf_service.BaseDocTemplate) as document:
        pdf=client.get(base+'/'+str(fresh.id)+'/pdf')
        assert document.call_args.kwargs['title'].startswith('W001 – Einstellbericht ')
    assert pdf.status_code==200 and pdf.data.startswith(b'%PDF')
    expected=f'W001_Einstellbericht_{fresh.id}_Stand_{fresh.version}.pdf'
    assert expected in pdf.headers['Content-Disposition'],pdf.headers['Content-Disposition']
print('PASS: five default zones without process values, separate mutable instances, unchanged stored/closed reports, add/delete/reorder preservation, no automatic reset, safe tool-first PDF filenames and download headers.')
