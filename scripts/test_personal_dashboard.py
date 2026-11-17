"""Synthetic per-account dashboard, authorization and persistence regressions."""
import runpy,re,json
from pathlib import Path
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.modules.profile.models import UserPreference
from factoryos.modules.profile.service import all_preferences

with app.app_context():
    def permission(name):
        row=Permission.query.filter_by(name=name).first()
        if not row:row=Permission(name=name);db.session.add(row)
        return row
    role=Role(name='dashboard-tools',active=True,permissions=[permission('tools.view')])
    db.session.add(role)
    alice=User(username='dashboard-alice',password_hash='unused',active=True,role=role)
    bob=User(username='dashboard-bob',password_hash='unused',active=True,role=Role(name='dashboard-store',active=True,permissions=[permission('inventory.view')]))
    db.session.add_all([alice,bob]);db.session.commit()
    def client(user):
        c=app.test_client()
        with c.session_transaction() as session:session['_user_id']=str(user.id);session['_fresh']=True
        return c
    def editor(c):
        response=c.get('/dashboard/customize');assert response.status_code==200
        html=response.get_data(as_text=True)
        token=re.search(r'name="access_csrf" value="([^"]+)"',html).group(1)
        boot=json.loads(re.search(r'id="factoryos-preferences-data" type="application/json">(.*?)</script>',html,re.S).group(1))
        choices=json.loads(re.search(r'id="dashboard-catalog-data" type="application/json">(.*?)</script>',html,re.S).group(1))
        return token,boot,choices
    a,b=client(alice),client(bob)
    before=UserPreference.query.count();token,boot,choices=editor(a);_,_,bchoices=editor(b)
    assert 'tool_list' in {t['key'] for t in choices['catalog']} and 'inventory' not in {t['key'] for t in choices['catalog']}
    assert 'inventory' in {t['key'] for t in bchoices['catalog']} and 'tool_list' not in {t['key'] for t in bchoices['catalog']}
    assert UserPreference.query.count()==before
    headers={'X-CSRF-Token':boot['csrf'],'X-FactoryOS-User':str(alice.id)}
    for tiles in (['inventory'],['tool_list','tool_list'],['https://evil.invalid'],[{}]):
        response=a.patch('/profile/preferences/dashboard',headers=headers,json={'values':{'tiles':tiles},'version':0});assert response.status_code==400,response.get_data(as_text=True)
    assert a.post('/dashboard/customize',data={}).status_code==403
    assert a.post('/dashboard/customize',data={'access_csrf':token,'account_id':bob.id,'version':0,'layout':'[]'}).status_code==403
    response=a.post('/dashboard/customize',data={'access_csrf':token,'account_id':alice.id,'version':0,'layout':json.dumps(['tool_list','profile'])})
    assert response.status_code==303
    assert all_preferences(alice.id)['dashboard']['values']['tiles']==['tool_list','profile']
    assert all_preferences(bob.id)['dashboard']['values']['tiles']!=['tool_list','profile']
    second_device=client(alice);html=second_device.get('/').get_data(as_text=True)
    assert 'Werkzeugliste' in html
    assert all_preferences(alice.id)['dashboard']['values']['tiles']==['tool_list','profile']
    assert a.post('/dashboard/customize',data={'access_csrf':token,'account_id':alice.id,'version':0,'layout':'[]'}).status_code==409
    record=db.session.get(UserPreference,(alice.id,'dashboard'));oldversion=record.version
    # Rights revocation removes both cards and offered metadata immediately on reload.
    role.permissions=[];db.session.commit()
    _,_,newchoices=editor(a);assert 'tool_list' not in {t['key'] for t in newchoices['catalog']}
    assert 'Werkzeugliste' not in a.get('/').get_data(as_text=True)
    assert record.version==oldversion
    role.permissions=[permission('tools.view')];db.session.commit()
    assert all_preferences(alice.id)['dashboard']['values']['tiles']==['tool_list','profile']
    # No-JS form: selection and explicit positions are also persisted.
    token,_,_=editor(a)
    response=a.post('/dashboard/customize',data={'access_csrf':token,'account_id':alice.id,'version':oldversion,'selected':['tool_list','profile'],'position_tool_list':'2','position_profile':'1'})
    assert response.status_code==303
    assert all_preferences(alice.id)['dashboard']['values']['tiles']==['profile','tool_list']
    version=all_preferences(alice.id)['dashboard']['version']
    assert a.post('/dashboard/customize',data={'access_csrf':token,'account_id':alice.id,'version':version,'layout':'[]'}).status_code==303
    assert 'Noch keine Kacheln ausgewählt' in a.get('/').get_data(as_text=True)
    root=client(db.session.merge(fixture['user']));html=root.get('/').get_data(as_text=True)
    sidebar=html.split('<aside')[1].split('</aside>')[0]
    assert sidebar.index('Dashboard')<sidebar.index('Produktion')<sidebar.index('Lager')<sidebar.index('Projekte')
    assert 'Lager' in html and '/warehouse/' in html
    assert 'no-store' in root.get('/').headers['Cache-Control']
print('PASS: per-account catalog and persistence, second device, server-side permission filtering/revocation, forged/duplicate/URL payload rejection, CSRF/account binding, stale conflict, no-JS order, empty choice, default warehouse card, sidebar order, private no-store and read-only GET.')
