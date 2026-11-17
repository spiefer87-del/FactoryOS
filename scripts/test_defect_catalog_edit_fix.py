"""Regression for the deployed AttributeError and read/edit/photo boundaries."""
import runpy
from pathlib import Path
from io import BytesIO
from PIL import Image
from sqlalchemy import text,inspect
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.article_defects.models import ArticleDefect,ArticleDefectPhoto
from factoryos.modules.article_defects.routes import photo_root
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from scripts.upgrade_defect_catalog import run_upgrade

with app.app_context():
    app.testing=True
    assert hasattr(ArticleDefect,'tool_no') and 'tool_no' in ArticleDefect.__table__.columns
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article'])
    entry=ArticleDefect(article_id=article.id,created_by_id=user.id,title='Nicht durchgefärbt',defect_type='Farbabweichungen / Farbschlieren',description='Farbe ist ungleichmäßig.',remedy='Batchanteil prüfen',archived=True)
    db.session.add(entry);db.session.commit();entry_id=entry.id
    # Existing data + missing DB column: the package must migrate, not mask the error.
    db.session.execute(text('ALTER TABLE article_defects DROP COLUMN tool_no'));db.session.commit()
    run_upgrade(True);run_upgrade();run_upgrade();db.session.expire_all()
    entry=db.session.get(ArticleDefect,entry_id)
    assert entry.title=='Nicht durchgefärbt' and entry.archived and entry.tool_no is None
    assert 'tool_no' in {c['name'] for c in inspect(db.engine).get_columns('article_defects')}
    photo_root().mkdir(parents=True,exist_ok=True)
    filename='regression-edit-fix.jpg';Image.new('RGB',(100,100),'white').save(photo_root()/filename,'JPEG')
    photo=ArticleDefectPhoto(defect_id=entry.id,filename=filename);db.session.add(photo);db.session.commit();photo_id=photo.id
    def client_for(person):
        c=app.test_client()
        with c.session_transaction() as s:s['_user_id']=str(person.id);s['_fresh']=True
        return c
    client=client_for(user);detail=f'/quality/defect-catalog/{entry.id}';edit=detail+'/edit';delete=f'/quality/defect-catalog/photo/{photo.id}/delete'
    response=client.get(detail);assert response.status_code==200
    assert 'Foto löschen' not in response.get_data(as_text=True) and '/delete' not in response.get_data(as_text=True)
    response=client.get(edit);assert response.status_code==200
    html=response.get_data(as_text=True);assert 'Foto löschen' in html and 'Gespeicherte Fotos' in html
    assert html.index('Gespeicherte Fotos')>html.index('Fehler speichern')
    with client.session_transaction() as s:csrf=s['access_csrf']
    data=dict(access_csrf=csrf,article_id=article.id,tool_no='',title=entry.title,defect_type=entry.defect_type,description=entry.description,remedy=entry.remedy,version=entry.version,archived='yes')
    assert client.post(edit,data={**data,'title':''}).status_code==422
    response=client.post(edit,data=data);assert response.status_code==303
    # None, existing and historical tool numbers, with and without photos.
    for number in (None,'HISTORICAL-TOOL',fixture['tool'].tool_no):
        entry.tool_no=number;db.session.commit();assert client.get(edit).status_code==200
    entry.tool_no=None;db.session.commit()
    def account(name,rights):
        permissions=[Permission.query.filter_by(name=r).one() for r in rights]
        person=User(username=name,password_hash='unused',active=True,role=Role(name=name,active=True,permissions=permissions));db.session.add(person);db.session.commit();return client_for(person)
    viewer=account('catalog-viewer',['defects.view'])
    editor=account('catalog-editor',['defects.view','defects.edit'])
    deleter=account('catalog-delete-only',['defects.view','defects.delete_photos'])
    assert viewer.get(detail).status_code==200 and viewer.get(edit).status_code==403
    assert editor.get(edit).status_code==200 and 'Foto löschen' not in editor.get(edit).get_data(as_text=True)
    assert deleter.get(edit).status_code==403
    for c in (viewer,editor,deleter):assert c.post(delete,data={'version':entry.version,'access_csrf':csrf}).status_code==403
    assert client.get(delete).status_code==405
    assert client.post(delete,data={'version':entry.version}).status_code==400
    assert client.post(delete,data={'access_csrf':csrf,'version':0}).status_code==409
    assert (photo_root()/filename).is_file()
    response=client.post(delete,data={'access_csrf':csrf,'version':entry.version});assert response.status_code==303 and response.location.endswith('/edit')
    assert client.get(response.location).status_code==200
    assert not (photo_root()/filename).exists() and db.session.get(ArticleDefectPhoto,photo_id) is None
    assert db.session.get(ArticleDefect,entry_id) is not None
    assert client.get(edit).status_code==200
print('PASS: mapped tool_no and legacy schema upgrade preserve records; edit archived+photo/no tool/historical tools; detail read-only; delete only below edit form; view/edit/delete ACL combinations, CSRF/stale versions, actual photo removal and return to working editor; text fields and record preserved')
