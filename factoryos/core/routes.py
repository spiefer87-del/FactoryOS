from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    send_file,
    url_for,
    request,flash,
)
from flask_login import current_user

from factoryos.core.storage import resolve_stored_file


bp = Blueprint("core", __name__)


@bp.route("/")
def home():

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    from factoryos.modules.profile.service import all_preferences
    from .dashboard_service import cards
    preference=all_preferences(current_user.id)['dashboard']
    return render_template('dashboard/home.html',tiles=cards(current_user.id,preference['values']['tiles']))

@bp.route('/dashboard/customize',methods=['GET','POST'])
def dashboard_customize():
    if not current_user.is_authenticated:return redirect(url_for('auth.login'))
    from .access_control import valid_csrf
    from .dashboard_service import permitted,cards,DEFAULT_TILES
    from factoryos.modules.profile.service import all_preferences,save_preferences,PreferenceConflict
    from factoryos.extensions import db
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm.exc import StaleDataError
    import json
    preference=all_preferences(current_user.id)['dashboard']
    keys=preference['values']['tiles'];error=None;status=200
    if request.method=='POST':
        if not valid_csrf() or request.form.get('account_id')!=str(current_user.id):abort(403)
        try:
            if request.form.get('reset')=='yes':
                allowed_keys={t['key'] for t in permitted(current_user.id)};keys=[k for k in DEFAULT_TILES if k in allowed_keys]
            elif request.form.get('layout'):
                keys=json.loads(request.form['layout'])
            else:
                keys=request.form.getlist('selected')
                keys.sort(key=lambda key:int(request.form.get('position_'+key,'999')))
            save_preferences(current_user.id,'dashboard',{'tiles':keys},int(request.form.get('version','-1')))
            flash('Dein Dashboard wurde im Benutzerkonto gespeichert.','success')
            return redirect(url_for('core.home'),code=303)
        except (PreferenceConflict,IntegrityError,StaleDataError):
            db.session.rollback();error='In einem anderen Fenster geändert. Bitte neu laden; dein Entwurf wurde nicht gespeichert.';status=409
        except (ValueError,TypeError) as exc:
            db.session.rollback();error=str(exc);status=422
    # Render only permitted tiles even when the submitted payload was manipulated.
    choices=permitted(current_user.id);allowed_keys={t['key'] for t in choices}
    safe_keys=[k for k in keys if type(k) is str and k in allowed_keys] if isinstance(keys,list) else []
    return render_template('dashboard/customize.html',choices=choices,selected=safe_keys,
        preference=preference,error=error,catalog=cards(current_user.id,[t['key'] for t in choices])),status


@bp.route("/storage/<path:storage_path>")
def storage_file(storage_path):

    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    try:
        file_path = resolve_stored_file(storage_path)
    except ValueError:
        abort(404)

    if not file_path.is_file():
        abort(404)

    return send_file(
        file_path,
        conditional=True,
    )
