from hashlib import sha256
import json
from flask import Blueprint,render_template,request,abort,session,flash,redirect,url_for
from flask_login import login_required,current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.production.services.booking_time_service import parse_local_start,eligible as start_eligible
from factoryos.modules.production.services.order_statistics import local_time,local_label
from .service import eligible,revision,validate,apply
from markupsafe import Markup
from factoryos.modules.production.services.booking_time_service import BookingOverlapError
from factoryos.modules.production.services.booking_time_service import eligible_end

bp=Blueprint('booking_review',__name__,url_prefix='/production/booking')

@bp.route('/<int:booking_id>/review',methods=['GET','POST'])
@login_required
@permission_required('production.view')
def detail(booking_id):
    row=TimeBooking.query.get_or_404(booking_id)
    permissions={'move':'production.edit_setup_time' if row.process in ('RUEST','ABRUEST') else 'production.edit_booking_time','cancel':'production.cancel_booking','delete':'production.delete_booking'}
    available={};hints=[]
    for action in permissions:
        try:eligible(row,action);available[action]=True
        except ValueError as exc:available[action]=False;hints.append(str(exc))
    blocked=hints[0] if not any(available.values()) else None
    allowed={action:available[action] and has_permission(current_user,right) for action,right in permissions.items()}
    can_start=False
    try:start_eligible(row);can_start=True
    except ValueError:pass
    if row.end_time and blocked:can_start=False
    can_end=False
    try:eligible_end(row);can_end=has_permission(current_user,'production.edit_booking_time')
    except ValueError:pass
    values={'start':local_time(row.start_time).strftime('%Y-%m-%dT%H:%M:%S'),'end':local_time(row.end_time).strftime('%Y-%m-%dT%H:%M:%S') if row.end_time else '', 'fold_start':'','fold_end':'','reason':'','action':next((a for a in permissions if allowed[a]),'move'),'revision':revision(row)}
    preview=False;error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400)
        values.update({key:request.form.get(key,'') for key in values})
        if values['action'] not in permissions:abort(400)
        needed=permissions[values['action']]
        if not has_permission(current_user,needed):abort(403)
        if values['revision']!=revision(row):abort(409,'Buchungen geändert. Bitte neu laden.')
        try:
            start=parse_local_start(values['start'],values['fold_start']) if values['action']=='move' else None
            end=parse_local_start(values['end'],values['fold_end']) if values['action']=='move' else None
            validate(row,values['action'],start,end,values['reason'])
            digest=sha256(json.dumps(values,sort_keys=True).encode()).hexdigest();key='booking_review_'+str(row.id)
            if request.form.get('intent')=='commit':
                if values['action']=='delete' and request.form.get('confirm_delete')!='yes':raise ValueError('Vollständiges Löschen muss ausdrücklich bestätigt werden.')
                if session.get(key)!=digest:raise ValueError('Bitte diese Änderung zuerst prüfen.')
                apply(row,values['action'],start,end,values['reason'],values['revision']);session.pop(key,None)
                if values['action']=='delete':
                    flash('Buchung vollständig gelöscht und Originaldaten protokolliert. Werkzeugbestand und Mengen unverändert.','success')
                    return redirect(url_for('production.booking_dashboard'),code=303)
                flash('Buchung mit Begründung korrigiert bzw. storniert. Mengen und Werkzeugbestand unverändert.','success')
                return redirect(url_for('booking_review.detail',booking_id=row.id),code=303)
            if request.form.get('intent')!='preview':abort(400)
            session[key]=digest;preview=True
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=400
            if isinstance(exc,BookingOverlapError):
                error=Markup('{} <a href="{}">Buchung #{} prüfen</a>').format(error,url_for('booking_review.detail',booking_id=exc.booking_id),exc.booking_id)
        except SQLAlchemyError:db.session.rollback();error='Keine Änderung gespeichert. Daten parallel geändert oder Datenbank belegt.';status=409
    return render_template('production/booking/review.html',booking=row,values=values,blocked=blocked,can_end=can_end,can_start=can_start and has_permission(current_user,'production.edit_booking_time'),preview=preview,error=error,local_label=local_label,can_move=allowed['move'],can_cancel=allowed['cancel'],can_delete=allowed['delete']),status

from . import repair_routes
