"""HTTP authorization regressions with synthetic users/in-memory database only."""
import runpy
import sys
import re
import os
import tempfile
import stat
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.admin.roles.models import Role
from factoryos.modules.admin.permissions.models import Permission
from factoryos.core.auth import has_permission
from factoryos.core.access_control import policy, CONFIRM_GET
from factoryos.modules.masterdata.articles.models import Article
from scripts.upgrade_access_control import run_upgrade
from factoryos.core.session_secret import ensure_session_secret, load_session_secret

saved_env=os.environ.pop("FACTORYOS_SECRET_KEY",None)
saved_path=os.environ.get("FACTORYOS_SECRET_KEY_FILE")
try:
    with tempfile.TemporaryDirectory() as temp:
        os.environ["FACTORYOS_SECRET_KEY_FILE"]=str(Path(temp)/"private.key")
        ensure_session_secret()
        first=load_session_secret()
        assert len(first)>=32
        assert stat.S_IMODE((Path(temp)/"private.key").stat().st_mode)==0o600
        ensure_session_secret()
        assert load_session_secret()==first
finally:
    if saved_env is not None:os.environ["FACTORYOS_SECRET_KEY"]=saved_env
    if saved_path is not None:os.environ["FACTORYOS_SECRET_KEY_FILE"]=saved_path
    else:os.environ.pop("FACTORYOS_SECRET_KEY_FILE",None)


def log_in(user_id):
    client=app.test_client()
    with client.session_transaction() as session:
        session["_user_id"]=str(user_id);session["_fresh"]=True
    return client


def admin_token(client):
    page=client.get("/admin/permissions/matrix")
    assert page.status_code==200
    html=page.get_data(as_text=True)
    return re.search(r'name="access_csrf" value="([^"]+)"',html).group(1),re.search(r'name="permissions_revision" value="([^"]+)"',html).group(1)


with app.app_context():
    admin=User.query.filter_by(username="test").one();aid=admin.id
    before_users=User.query.count()
    run_upgrade(app,True);run_upgrade(app);run_upgrade(app)
    assert User.query.count()==before_users
    perms={p.name:p for p in Permission.query.all()}
    production=Role(name="production-security",active=True,permissions=[perms["production.start"],perms["production.stop"],perms["tools.view"]])
    empty_role=Role(name="no-rights",active=True)
    employee=User(username="security-production",password_hash="synthetic",active=True,role=production)
    nobody=User(username="security-no-rights",password_hash="synthetic",active=True,role=empty_role)
    db.session.add_all([production,empty_role,employee,nobody]);db.session.commit()
    uid,nid,rid=employee.id,nobody.id,production.id
    prod=log_in(uid);root=log_in(aid);zero=log_in(nid)
    # A cookie signed with a different/old signing key must not authenticate.
    from flask import Flask
    wrong_app=Flask("wrong-key-test");wrong_app.secret_key="different-synthetic-key-for-regression-test"
    forged=app.test_client()
    cookie=wrong_app.session_interface.get_signing_serializer(wrong_app).dumps({"_user_id":str(aid),"_fresh":True})
    forged.set_cookie("session",cookie)
    assert forged.get("/admin/users/").status_code==302
    for path in ("/admin/","/admin/users/","/admin/users/create",f"/admin/users/edit/{uid}","/admin/roles/","/admin/permissions/matrix",f"/admin/permissions/roles/{rid}"):
        assert prod.get(path).status_code==403,path
    assert prod.post("/admin/users/create",data={"username":"ESCALATED","password":"Synthetic-test-password","role_id":str(admin.role_id)}).status_code==403
    assert prod.post(f"/admin/users/edit/{uid}",data={"username":employee.username,"role_id":str(admin.role_id),"active":"1"}).status_code==403
    assert prod.post(f"/admin/permissions/roles/{rid}",data={"permissions":[str(perms["users.create"].id)]}).status_code==403
    assert not User.query.filter_by(username="ESCALATED").first()
    assert db.session.get(User,uid).role_id==rid
    assert not has_permission(employee,"users.create")
    assert '/admin/users/' not in prod.get("/").get_data(as_text=True)
    assert '/admin/permissions/matrix' not in prod.get("/").get_data(as_text=True)
    # All registered protected endpoints deny a user without permissions before any lookup/mutation.
    checked=0
    for rule in app.url_map.iter_rules():
        spec=policy(rule.endpoint,app.view_functions.get(rule.endpoint))
        if not spec or spec=="LOGIN":continue
        path=rule.rule
        for match in re.findall(r'<(?:[^:>]+:)?([^>]+)>',path):
            path=re.sub(r'<(?:[^:>]+:)?'+re.escape(match)+'>',"999999",path,count=1)
        for method in sorted(rule.methods & {"GET","POST","PATCH"}):
            result=zero.open(path,method=method)
            assert result.status_code==403,(rule.endpoint,method,result.status_code)
            checked+=1
    assert checked>150
    # Permission enforcement for tools/production/quality, including direct POST and images.
    assert zero.get("/masterdata/tools/list").status_code==403
    assert prod.get("/masterdata/tools/list").status_code==200
    assert prod.post("/masterdata/tools/create",data={}).status_code==403
    assert zero.post("/production/start",data={}).status_code==403
    assert zero.get("/static/uploads/tool_errors/file.png").status_code==403
    assert zero.get("/storage/Stammdaten/Werkzeuge/W1/Werkzeugbilder/file.png").status_code==403
    # Admin has protected full access even if its matrix memberships are empty.
    assert has_permission(admin,"users.create")
    csrf,revision=admin_token(root)
    assert root.post("/admin/users/create",data={}).status_code==400
    assert root.post("/admin/users/",data={"access_csrf":csrf}).status_code==405
    assert root.post(f"/admin/permissions/roles/{rid}",data={"access_csrf":csrf}).status_code==405
    assert root.get(f"/admin/permissions/roles/{rid}").status_code==302
    assert root.post("/admin/permissions/matrix",data={"access_csrf":csrf,"permissions_revision":"stale"}).status_code==409
    original={p.name for p in production.permissions}
    assert root.post("/admin/permissions/matrix",data={"access_csrf":csrf,"permissions_revision":revision,f"role_{rid}":["99999999"]}).status_code==400
    assert {p.name for p in production.permissions}==original
    # Actual authorized create/edit works; no last-admin/self-deletion lockout.
    created=root.post("/admin/users/create",data={"access_csrf":csrf,"username":"created-secure","password":"Synthetic-test-password","role_id":str(rid)})
    assert created.status_code==302
    target=User.query.filter_by(username="created-secure").one();tid=target.id
    assert root.post(f"/admin/users/edit/{tid}",data={"access_csrf":csrf,"username":"renamed-secure","role_id":str(rid),"active":"1"}).status_code==302
    assert root.post(f"/admin/users/delete/{aid}",data={"access_csrf":csrf}).status_code==400
    assert root.post(f"/admin/roles/delete/{admin.role_id}",data={"access_csrf":csrf}).status_code==400
    assert root.post(f"/admin/roles/delete/{rid}",data={"access_csrf":csrf}).status_code==400
    assert root.post(f"/admin/roles/edit/{admin.role_id}",data={"access_csrf":csrf,"name":"not-admin","active":"1"}).status_code==400
    # Delegated user management does not allow privileged role/account takeover.
    production.permissions.extend([perms["users.view"],perms["users.create"],perms["users.edit"],perms["users.delete"]]);db.session.commit()
    assert prod.get("/admin/users/").status_code==200
    assert prod.get(f"/admin/users/edit/{aid}").status_code==403
    prod.get("/admin/users/create")
    with prod.session_transaction() as session: pcsrf=session["access_csrf"]
    assert prod.post("/admin/users/create",data={"access_csrf":pcsrf,"username":"NO-ADMIN","password":"Synthetic-test-password","role_id":str(admin.role_id)}).status_code==403
    assert prod.get("/admin/roles/").status_code==403
    # Previously destructive GETs now only display confirmation.
    article=Article(article_no="CONFIRM-DELETE",article_name="Disposable test")
    db.session.add(article);db.session.commit();article_id=article.id
    delete_path=f"/masterdata/articles/delete/{article_id}"
    assert root.get(delete_path).status_code==200
    assert db.session.get(Article,article_id)
    assert root.post(delete_path).status_code==400
    assert root.post(delete_path,data={"access_csrf":csrf}).status_code==302
    assert db.session.get(Article,article_id) is None
    # Successful matrix writes take effect on the next request; admin cannot be unchecked.
    csrf,revision=admin_token(root)
    payload={"access_csrf":csrf,"permissions_revision":revision}
    for role in Role.query.all():
        if role.name!="admin":payload[f"role_{role.id}"]=[str(p.id) for p in role.permissions]
    payload[f"role_{empty_role.id}"]=[str(perms["tools.view"].id)]
    assert root.post("/admin/permissions/matrix",data=payload).status_code==302
    assert zero.get("/masterdata/tools/list").status_code==200
    assert has_permission(admin,"users.delete")
    assert root.post("/admin/permissions/matrix",data=payload).status_code==409
    quality=Role(name="quality-security",active=True,permissions=[perms["quality.view"],perms["quality.inspect"]])
    qa_user=User(username="security-quality",password_hash="synthetic",active=True,role=quality)
    db.session.add(qa_user);db.session.commit()
    assert log_in(qa_user.id).get("/quality/inspection-plans/create").status_code==200
    assert policy("future.unreviewed_route")=="DENY"
    # Inactive roles and users cannot retain elevated sessions.
    production.active=False;db.session.commit()
    assert prod.get("/masterdata/tools/list").status_code==403
    production.active=True;employee.active=False;db.session.commit()
    assert prod.get("/admin/users/").status_code==403
    assert prod.get("/logout").status_code==302
    print(f"PASS: {checked} denied route/method combinations; reproduced privilege-escalation paths blocked; explicit grants, protected admin, CSRF, matrix conflict, delegate restrictions, inactive role/user, GET confirmation and POST execution, upgrade twice.")
