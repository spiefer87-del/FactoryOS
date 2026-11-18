from datetime import datetime,timedelta
from types import SimpleNamespace
from hashlib import sha256
import json
from flask import request,render_template,abort,session,redirect,url_for,flash
from flask_login import login_required
from sqlalchemy import or_,cast,String
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,role_required
from factoryos.core.access_control import valid_csrf
from factoryos.modules.production.models import TimeBooking,SetupOperation
from factoryos.modules.orders.models import Order
from factoryos.models.machine import Machine
from factoryos.modules.production.services.booking_time_service import parse_local_start
from factoryos.modules.production.services.order_statistics import local_time,local_label,duration
from .routes import bp
from . import admin_repair

@bp.get('/journal')
@login_required
@permission_required('production.view')
def journal():
    query=TimeBooking.query.outerjoin(Order,TimeBooking.order_id==Order.id).outerjoin(Machine,TimeBooking.machine_id==Machine.id)
    search=request.args.get('q','').strip()[:100]
    if search:query=query.filter(or_(cast(TimeBooking.id,String).contains(search),Order.order_no.contains(search),Machine.machine_no.contains(search),TimeBooking.tool_no.contains(search),TimeBooking.process.contains(search)))
    start=end=None;error=None
    try:
        if request.args.get('von'):start=parse_local_start(request.args['von']+'T00:00')
        if request.args.get('bis'):
            last=datetime.strptime(request.args['bis'],'%Y-%m-%d')+timedelta(days=1)
            end=parse_local_start(last.strftime('%Y-%m-%dT00:00'))
        if start and end and start>=end:raise ValueError('Beginn liegt nach dem Ende.')
    except (ValueError,OverflowError):error='Bitte einen gültigen Zeitraum eingeben.'
    if start:query=query.filter(or_(TimeBooking.end_time.is_(None),TimeBooking.end_time>start))
    if end:query=query.filter(TimeBooking.start_time<end)
    page=query.order_by(TimeBooking.start_time.desc(),TimeBooking.id.desc()).paginate(page=max(1,request.args.get('page',1,type=int)),per_page=50,error_out=False)
    from factoryos.modules.production.services.idle_context_service import idle_views,time_summary
    from factoryos.modules.production.models import ProductionCalendarSettings
    from factoryos.modules.production.services.calendar_service import get_calendar_exceptions
    rows=query.all() if not error else [];now=datetime.utcnow();views=idle_views(rows,now)
    basis=request.args.get('basis','working');basis=basis if basis in ('working','calendar') else 'working'
    calendar=(ProductionCalendarSettings.query.first() or SimpleNamespace(week_start_day=0,week_start_time='04:30',week_end_day=5,week_end_time='06:00')) if basis=='working' else None
    summary=time_summary(rows,views,now=now,start=start,end=end,calendar=calendar,exceptions=get_calendar_exceptions())
    return render_template('production/booking/journal.html',page=page,search=search,local_label=local_label,
        views=views,summary=summary,duration=duration,error=error,basis=basis),400 if error else 200

@bp.route('/<int:booking_id>/repair',methods=['GET','POST'])
@login_required
@role_required('admin')
def repair(booking_id):
    row=TimeBooking.query.get_or_404(booking_id)
    values=dict(action='move',start=local_time(row.start_time).strftime('%Y-%m-%dT%H:%M:%S'),end=local_time(row.end_time).strftime('%Y-%m-%dT%H:%M:%S') if row.end_time else '',fold_start='',fold_end='',reason='',revision=admin_repair.revision(row))
    preview=None;error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400)
        values.update({k:request.form.get(k,'') for k in values})
        try:
            if values['revision']!=admin_repair.revision(row):raise ValueError('Daten inzwischen geändert. Bitte neu laden und erneut prüfen.')
            start=parse_local_start(values['start'],values['fold_start']) if values['action']=='move' else None
            end=parse_local_start(values['end'],values['fold_end']) if values['action']=='move' and values['end'] else None
            preview=admin_repair.plan(row,values['action'],start,end,values['reason'])
            digest=sha256(json.dumps(values,sort_keys=True).encode()).hexdigest();key='admin_repair_'+str(row.id)
            if request.form.get('intent')=='commit':
                if session.get(key)!=digest:raise ValueError('Bitte diese Reparatur zuerst prüfen.')
                if request.form.get('acknowledge')!='yes':raise ValueError('Auswirkungen müssen ausdrücklich bestätigt werden.')
                admin_repair.apply(row,values['action'],start,end,values['reason'],values['revision']);session.pop(key,None)
                flash('Administrator-Reparatur gespeichert und Originaldaten protokolliert. Werkzeugbestand und Mengen separat kontrollieren.','success')
                return redirect(url_for('booking_review.journal'),code=303)
            if request.form.get('intent')!='preview':abort(400)
            session[key]=digest
        except PermissionError:db.session.rollback();abort(403)
        except ValueError as exc:db.session.rollback();error=str(exc);status=400;preview=None
        except SQLAlchemyError:db.session.rollback();error='Keine Reparatur gespeichert. Datenbankkonflikt; bitte neu laden und erneut prüfen.';status=409;preview=None
    return render_template('production/booking/admin_repair.html',booking=row,values=values,preview=preview,error=error,local_label=local_label,operations=admin_repair.operations(row)),status
