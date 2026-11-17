import runpy
from pathlib import Path
from io import BytesIO
from PIL import Image
fixture=runpy.run_path(str(Path(__file__).resolve().parent/'test_sampling_orders.py'))
app=fixture['app']
from factoryos.extensions import db
from factoryos.modules.article_defects.models import ArticleDefect,ArticleDefectPhoto
from factoryos.modules.article_defects.routes import photo_root
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.core.models.change_log import ChangeLog
from scripts.upgrade_defect_catalog import run_upgrade

with app.app_context():
    app.testing=True;run_upgrade();run_upgrade()
    user=db.session.merge(fixture['user']);article=db.session.merge(fixture['article'])
    entry=ArticleDefect(article_id=article.id,created_by_id=user.id,title='Farbabweichung an der Sichtfläche',tool_no='COR248',defect_type='Farbabweichungen / Farbschlieren',description='Ungleichmäßige Einfärbung an der linken Sichtfläche.\nNach dem Materialwechsel wiederholt aufgetreten. <kein HTML>',remedy='Masterbatch-Anteil prüfen und Materialwechsel dokumentieren.')
    db.session.add(entry);db.session.flush();photo_root().mkdir(parents=True,exist_ok=True)
    filename='pdf-delete-test.jpg'
    from PIL import ImageDraw
    photo=Image.new('RGB',(1100,650),'#e9eef4');draw=ImageDraw.Draw(photo);draw.rounded_rectangle((120,100,980,550),100,fill='#164e63');draw.ellipse((300,220,650,430),fill='#75bac3');photo.save(photo_root()/filename,'JPEG')
    db.session.add(ArticleDefectPhoto(defect_id=entry.id,filename=filename));db.session.commit()
    client=app.test_client()
    with client.session_transaction() as s:s['_user_id']=str(user.id);s['_fresh']=True
    response=client.get(f'/quality/defect-catalog/{entry.id}/pdf')
    assert response.status_code==200 and response.mimetype=='application/pdf' and response.data.startswith(b'%PDF')
    assert response.headers['Cache-Control']=='private, no-store'
    output=Path(__file__).resolve().parents[1]/'tmp/pdfs';output.mkdir(parents=True,exist_ok=True)
    (output/'defect-example.pdf').write_bytes(response.data)
    assert client.get('/quality/defect-catalog/pdf?article_id='+str(article.id)).status_code==200
    assert client.get('/quality/defect-catalog/pdf').status_code==200
    short=entry.description
    entry.description=('Prüfhinweis mit Umlauten: Größe, Öl, Wärme. Lange Beschreibung und Maßnahme.\n'*100);db.session.commit()
    response=client.get(f'/quality/defect-catalog/{entry.id}/pdf');assert response.status_code==200
    (output/'defect-long.pdf').write_bytes(response.data)
    entry.description=short;db.session.commit()
    path=f'/quality/defect-catalog/{entry.id}/delete'
    assert client.get(path).status_code==200
    with client.session_transaction() as s:csrf=s['access_csrf']
    data=dict(access_csrf=csrf,version=entry.version,reason='Fehleintrag aus der Testphase',confirmed='yes')
    assert client.post(path,data={}).status_code==400
    assert client.post(path,data={**data,'version':0}).status_code==409
    assert client.post(path,data={**data,'confirmed':''}).status_code==422
    viewer=User(username='pdf-viewer',password_hash='unused',active=True,role=Role(name='pdf-viewer',active=True,permissions=[Permission.query.filter_by(name='defects.view').one()]));db.session.add(viewer);db.session.commit()
    denied=app.test_client()
    with denied.session_transaction() as s:s['_user_id']=str(viewer.id);s['_fresh']=True
    assert denied.get(f'/quality/defect-catalog/{entry.id}/pdf').status_code==403
    assert denied.get(path).status_code==403 and denied.post(path,data=data).status_code==403
    viewer.role.permissions.append(Permission.query.filter_by(name='defects.delete').one());db.session.commit()
    assert denied.get(path).status_code==403
    from sqlalchemy import text
    db.session.execute(text('CREATE TABLE defect_extra_reference (id INTEGER PRIMARY KEY,defect_id INTEGER REFERENCES article_defects(id))'))
    db.session.execute(text('INSERT INTO defect_extra_reference (defect_id) VALUES (:id)'),{'id':entry.id});db.session.commit()
    assert client.post(path,data=data).status_code==409
    assert (photo_root()/filename).exists()
    db.session.execute(text('DROP TABLE defect_extra_reference'));db.session.commit()
    entry_id=entry.id
    assert client.post(path,data=data).status_code==303
    assert db.session.get(ArticleDefect,entry_id) is None and not ArticleDefectPhoto.query.filter_by(defect_id=entry_id).first()
    assert not (photo_root()/filename).exists()
    audit=ChangeLog.query.filter_by(category='article_defect',action='delete').one()
    assert audit.changes['deleted_defect']['old']['title']=='Farbabweichung an der Sichtfläche'
    assert client.get(f'/quality/defect-catalog/{entry_id}').status_code==404
    assert client.get('/quality/defect-catalog/pdf').status_code==200
print('PASS: entry/article/all PDFs, long escaped German text, photo embedding, private PDF access, protected delete confirmation/CSRF/stale version, full child/file removal, retained audit and empty PDF')
