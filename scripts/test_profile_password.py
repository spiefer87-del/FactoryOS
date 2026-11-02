"""Account password change tests against disposable SQLite users."""
import sys
import runpy
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.profile.models import UserPreference


def token(client):
    html=client.get("/profile/").get_data(as_text=True)
    seed=json.loads(re.search(r'<script id="factoryos-preferences-data" type="application/json">(.*?)</script>',html,re.S).group(1))
    return seed,html


with app.app_context():
    user=User(username="password-owner",active=True);user.set_password("Old-password-123")
    other=User(username="password-other",active=True);other.set_password("Other-password-123")
    db.session.add_all([user,other]);db.session.commit()
    uid,oid=user.id,other.id
    db.session.add(UserPreference(user_id=uid,section="appearance",values={"density":"compact","accent":"teal"}))
    db.session.commit()
    original=user.password_hash;other_hash=other.password_hash
    client=app.test_client()
    assert client.post("/profile/password",data={}).status_code==302
    client.post("/login",data={"username":"password-owner","password":"Old-password-123"})
    seed,html=token(client)
    assert html.count('type="password"')==3
    assert html.count('data-password-toggle=')==3
    assert 'autocomplete="current-password"' in html and 'autocomplete="new-password"' in html
    assert 'profile_password.css' in html and 'profile_password.js' in html
    assert original not in html and "Old-password-123" not in html
    data={"csrf_token":seed["csrf"],"account_id":str(uid),"current_password":"Old-password-123","new_password":"New-password-456","confirm_password":"New-password-456"}
    assert client.get("/profile/password").status_code==405
    assert client.post("/profile/password",data={**data,"csrf_token":"bad"}).status_code==400
    assert client.post("/profile/password",data={**data,"account_id":str(oid)}).status_code==400
    invalid=[{"current_password":"incorrect"},
             {"new_password":"short","confirm_password":"short"},
             {"new_password":" "*12,"confirm_password":" "*12},
             {"new_password":"x"*129,"confirm_password":"x"*129},
             {"confirm_password":"not-matching"},
             {"new_password":"Old-password-123","confirm_password":"Old-password-123"},
             {"current_password":"x"*1025}]
    for change in invalid:
        response=client.post("/profile/password",data={**data,**change},follow_redirects=True)
        assert response.status_code==200
        page=response.get_data(as_text=True)
        assert 'value="Old-password-123"' not in page and 'value="New-password-456"' not in page
        db.session.expire_all()
        assert db.session.get(User,uid).password_hash==original
    client.set_cookie("remember_token","synthetic-stale-cookie")
    response=client.post("/profile/password",data=data)
    assert response.status_code==302 and response.location.endswith("/login")
    assert any("remember_token=;" in header for header in response.headers.getlist("Set-Cookie"))
    with client.session_transaction() as session:
        assert "_user_id" not in session and "preferences_csrf" not in session
    db.session.expire_all()
    changed=db.session.get(User,uid)
    assert changed.password_hash!=original and changed.check_password("New-password-456")
    assert not changed.check_password("Old-password-123")
    assert db.session.get(User,oid).password_hash==other_hash
    assert changed.role_id is None and changed.username=="password-owner"
    assert db.session.get(UserPreference,(uid,"appearance")).values=={"density":"compact","accent":"teal"}
    logs=ChangeLog.query.filter_by(entity_type="user",entity_id=uid,action="password_change").all()
    assert len(logs)==1 and logs[0].user_id==uid and logs[0].changes=={"password_changed":True}
    audit=json.dumps(logs[0].changes)
    for secret in (original,changed.password_hash,"Old-password-123","New-password-456"):
        assert secret not in audit
    assert client.get("/profile/").status_code==302
    client.post("/login",data={"username":"password-owner","password":"Old-password-123"})
    assert client.get("/profile/").status_code==302
    client.post("/login",data={"username":"password-owner","password":"New-password-456"})
    seed,_=token(client)
    # Leading/trailing whitespace is intentional and must work at login too.
    spaced="  Long passphrase with spaces  "
    client.post("/profile/password",data={**data,"csrf_token":seed["csrf"],"current_password":"New-password-456","new_password":spaced,"confirm_password":spaced})
    client.post("/login",data={"username":"password-owner","password":spaced})
    assert client.get("/profile/").status_code==200
    seed,_=token(client)
    disabled=db.session.get(User,uid);disabled.active=False;db.session.commit()
    assert client.post("/profile/password",data={**data,"csrf_token":seed["csrf"]}).status_code==403
print("PASS: auth/CSRF/account binding, old-password validation, new length/confirmation/difference, no secret echoes or audit values, own hash only, logout and new login, whitespace, disabled account, three accessible reveal controls.")
