"""Account-scoped settings, actual logout/login, CSRF, versions and upgrade."""
import sys
import runpy
import re
import json
from pathlib import Path
from sqlalchemy import inspect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
fixture=runpy.run_path(str(ROOT/"scripts/test_sampling_orders.py"))
app=fixture["app"]
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.modules.profile.models import UserPreference
from factoryos.modules.profile.service import DEFAULTS
from scripts.upgrade_user_preferences import run_upgrade


def boot(client):
    response=client.get("/profile/")
    assert response.status_code==200
    html=response.get_data(as_text=True)
    return json.loads(re.search(r'<script id="factoryos-preferences-data" type="application/json">(.*?)</script>',html,re.S).group(1)),html


def headers(seed):
    return {"X-CSRF-Token":seed["csrf"],"X-FactoryOS-User":str(seed["user_id"])}


with app.app_context():
    existing_users=User.query.count()
    db.session.remove()
    UserPreference.__table__.drop(bind=db.engine)
    run_upgrade(True)
    assert not inspect(db.engine).has_table("user_preferences")
    run_upgrade();run_upgrade()
    assert User.query.count()==existing_users
    alice=User(username="alice-prefs",active=True);alice.set_password("test-password")
    bob=User(username="bob-prefs",active=True);bob.set_password("test-password")
    db.session.add_all([alice,bob]);db.session.commit()
    aid,bid=alice.id,bob.id
    client=app.test_client()
    assert client.get("/profile/").status_code==302
    assert client.get("/profile/preferences/articles.columns").status_code==401
    assert client.post("/login",data={"username":"alice-prefs","password":"test-password"}).status_code==302
    seed,html=boot(client)
    assert seed["user_id"]==aid and 'href="/profile/"' in html and "Mein Profil" in html
    assert "Darstellung" in html and "Akzentfarbe" in html
    assert client.patch("/profile/preferences/articles.columns",json={"values":{"sampling":False},"version":0}).status_code==403
    assert client.patch("/profile/preferences/articles.columns",headers={**headers(seed),"X-FactoryOS-User":str(bid)},json={"values":{"sampling":False},"version":0}).status_code==403
    response=client.patch("/profile/preferences/articles.columns",headers=headers(seed),json={"values":{"sampling":False},"version":0})
    assert response.status_code==200
    version=response.json["version"]
    assert response.json["values"]["sampling"] is False
    # No arbitrary user IDs, unknown keys, hidden identity, or non-boolean values.
    bad_payloads=[{"values":{"sampling":"false"},"version":version},
                  {"values":{"article_no":False},"version":version},
                  {"values":{"sampling":True},"version":version,"user_id":bid},
                  {"values":{"unknown":False},"version":version},
                  {"values":{"sampling":True},"version":True}]
    for payload in bad_payloads:
        assert client.patch("/profile/preferences/articles.columns",headers=headers(seed),json=payload).status_code==400
    stale=client.patch("/profile/preferences/articles.columns",headers=headers(seed),json={"values":{"customer":False},"version":0})
    assert stale.status_code==409 and stale.json["current"]["values"]["sampling"] is False
    # Patch a different section without affecting article columns.
    assert client.patch("/profile/preferences/tools.columns",headers=headers(seed),json={"values":{"location":False},"version":0}).status_code==200
    assert client.patch("/profile/preferences/appearance",headers=headers(seed),json={"values":{"accent":"teal","density":"compact"},"version":0}).status_code==200
    assert client.patch("/profile/preferences/appearance",headers=headers(seed),json={"values":{"accent":"<script>"},"version":1}).status_code==400
    assert client.get("/profile/preferences/unknown").status_code==404
    # A completely new client simulates a different browser/device and login.
    client.get("/logout")
    fresh=app.test_client()
    fresh.post("/login",data={"username":"alice-prefs","password":"test-password"})
    restored,html=boot(fresh)
    assert restored["sections"]["articles.columns"]["values"]["sampling"] is False
    assert restored["sections"]["tools.columns"]["values"]["location"] is False
    assert 'data-ui-accent="teal"' in html and 'data-ui-density="compact"' in html
    assert "no-store" in fresh.get("/profile/preferences/appearance").headers["Cache-Control"]
    second=app.test_client();second.post("/login",data={"username":"bob-prefs","password":"test-password"})
    bob_seed,bob_html=boot(second)
    assert bob_seed["sections"]["articles.columns"]["values"]["sampling"] is True
    assert 'data-ui-accent="blue"' in bob_html
    assert UserPreference.query.filter_by(user_id=bid).count()==0  # Reads never create prefs.
    # Profile standard reset saves explicit defaults, preventing reimport of old local state.
    assert fresh.post("/profile/",data={"csrf_token":restored["csrf"],"action":"articles.columns","version":version}).status_code==302
    reset,_=boot(fresh)
    assert reset["sections"]["articles.columns"]["version"]>0
    assert reset["sections"]["articles.columns"]["values"]==DEFAULTS["articles.columns"]
    assert fresh.post("/profile/",data={"csrf_token":reset["csrf"],"action":"appearance","version":reset["sections"]["appearance"]["version"],"density":"comfortable","accent":"violet"}).status_code==302
    changed,changed_html=boot(fresh)
    assert 'data-ui-accent="violet"' in changed_html
    assert 'data-ui-density="comfortable"' in changed_html
    tools_html=fresh.get("/masterdata/tools/list").get_data(as_text=True)
    assert 'js/tool_columns.js' in tools_html
    assert 'localStorage.setItem' not in tools_html and 'importLegacyToolColumns' in tools_html
    assert 'data-ui-accent="violet"' in tools_html
    assert 'no-store' in fresh.get("/profile/").headers['Cache-Control']
    assert fresh.post("/profile/",data={"action":"appearance"}).status_code==400
    # Appearance cannot change identity, role or permissions.
    assert db.session.get(User,aid).username=="alice-prefs" and db.session.get(User,aid).role_id is None
    # Relationship cascade leaves no orphaned personal settings.
    disposable=User(username="prefs-delete",password_hash="test",active=True)
    db.session.add(disposable);db.session.flush();did=disposable.id
    db.session.add(UserPreference(user_id=did,section="appearance",values=DEFAULTS["appearance"]))
    db.session.commit();db.session.delete(disposable);db.session.commit()
    assert UserPreference.query.filter_by(user_id=did).count()==0
print("PASS: idempotent isolated migration, profile/navbar, per-account data, separate devices/logout/login, defaults/read-only GET, CSRF/account binding, strict validation, version conflict, section independence, reset, appearance, deletion cascade.")
