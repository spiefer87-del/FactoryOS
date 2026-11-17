from datetime import datetime,date
from zoneinfo import ZoneInfo
from uuid import uuid4
from flask import request,render_template,redirect,url_for,abort,flash,send_file,current_app,jsonify
from flask_login import login_required,current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError,OperationalError
from factoryos.extensions import db
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.core.storage import storage_root
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.tool_errors.models import ToolError
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.article_defects.photos import prepare_photo
from ..workspace_models import Workspace,Member,Task,Link,WorkTime,Report,ReportPhoto,ToolPartEvent,Audit
from ..services.workspace_service import (CLOSED,TASK_STATES,permitted,mine_clause,project,lock,version,audit,required,quantity,local_time,check_interval,berlin,input_time)
from . import bp

def csrf():
    if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')

def failed(error,project_id=None,status=422):
    db.session.rollback()
    return render_template('projects/workspace_error.html',message=str(error),project_id=project_id),status

def members(item):
    ids={m.user_id for m in Member.query.filter_by(project_id=item.id)}
    if item.project_leader_id:ids.add(item.project_leader_id)
    return ids

def selected_link(item,data):
    if not data.get('link_id'):return None
    link=Link.query.filter_by(id=data.get('link_id',type=int),project_id=item.id).first_or_404()
    if (link.sampling_id and not has_permission(current_user,'sampling.view')) or (link.error_id and not has_permission(current_user,'tool_error.view')):abort(403)
    return link.id

@bp.route('/')
@bp.route('/dashboard')
@bp.route('/home',endpoint='projects_home')
@login_required
@permission_required('projects.view')
def dashboard():
    q=request.args.get('q','').strip()[:100];scope=request.args.get('scope','mine');archive=request.args.get('archive')=='1'
    base=Order.query.filter(Order.is_project.is_(True))
    if scope!='all' or not permitted('view_all'):base=base.filter(mine_clause());scope='mine'
    base=base.filter(Order.status.in_(CLOSED) if archive else ~Order.status.in_(CLOSED))
    if q:base=base.filter(or_(Order.order_no.ilike('%'+q+'%'),Order.tool_no.ilike('%'+q+'%'),Order.description.ilike('%'+q+'%'),Order.article.ilike('%'+q+'%')))
    page=base.order_by(Order.updated_at.desc(),Order.id.desc()).paginate(page=max(1,request.args.get('page',1,type=int) or 1),per_page=30,error_out=False)
    own=Order.query.filter(Order.is_project.is_(True),mine_clause(),~Order.status.in_(CLOSED))
    active=WorkTime.query.filter_by(user_id=current_user.id,cancelled=False).filter(WorkTime.ended_at.is_(None)).all()
    legacy=TimeBooking.query.filter_by(user_id=current_user.id,process='PROJEKT',machine_id=None).filter(TimeBooking.end_time.is_(None)).all()
    tasks=Task.query.filter(Task.assignee_id==current_user.id,Task.status!='done',Task.project_id.in_(db.select(Order.id).where(Order.is_project.is_(True),mine_clause(),~Order.status.in_(CLOSED)))).order_by(Task.due_date.is_(None),Task.due_date).limit(30).all()
    return render_template('projects/workspace_home.html',page=page,q=q,scope=scope,archive=archive,active=active,legacy=legacy,tasks=tasks,count=own.count(),today=datetime.now(ZoneInfo('Europe/Berlin')).date(),states=TASK_STATES,fmt=berlin,view_all=permitted('view_all'))

@bp.route('/create',methods=['GET','POST'])
@login_required
@permission_required('projects.create')
def projects_create():
    if not permitted('view'):abort(403)
    if request.method=='POST':
        csrf()
        try:
            lock();number=required(request.form,'order_no',50);description=required(request.form,'description',255)
            tool=None
            if request.form.get('tool_id'):tool=Tool.query.get_or_404(request.form.get('tool_id',type=int))
            item=Order(order_no=number,description=description,tool_no=tool.tool_no if tool else None,is_project=True,status='offen',target_qty=0,project_leader_id=current_user.id)
            db.session.add(item);db.session.flush();db.session.add(Workspace(order_id=item.id));db.session.add(Member(project_id=item.id,user_id=current_user.id));audit(item,'Projekt angelegt',{'description':description});db.session.commit()
            return redirect(url_for('projects.detail',project_id=item.id),303)
        except ValueError as error:return failed(error)
        except IntegrityError:return failed('Projektnummer bereits vorhanden.')
    return render_template('projects/workspace_create.html',tools=Tool.query.order_by(Tool.tool_no).all())

@bp.route('/<int:project_id>')
@login_required
@permission_required('projects.view')
def detail(project_id):
    item=project(project_id);workspace=db.session.get(Workspace,item.id)
    if not workspace:abort(503,'Projektmigration zuerst ausführen.')
    reports=Report.query.filter_by(project_id=item.id).order_by(Report.id.desc()).limit(50).all()
    times=WorkTime.query.filter_by(project_id=item.id).order_by(WorkTime.started_at.desc()).limit(200).all()
    total=sum(((t.ended_at or datetime.utcnow())-t.started_at).total_seconds() for t in WorkTime.query.filter_by(project_id=item.id,cancelled=False))
    selected_tool=Tool.query.filter_by(tool_no=item.tool_no).first() if item.tool_no else None
    return render_template('projects/workspace_detail.html',item=item,version=workspace.version,closed=item.status in CLOSED,states=TASK_STATES,fmt=berlin,input_time=input_time,permitted=permitted,
        members=Member.query.filter_by(project_id=item.id).all(),users=User.query.filter_by(active=True).order_by(User.username).all() if permitted('manage') else [],
        tasks=Task.query.filter_by(project_id=item.id).order_by(Task.id).all(),links=Link.query.filter_by(project_id=item.id).all(),reports=reports,times=times,total=round(total/3600,2),
        legacy=TimeBooking.query.filter_by(order_id=item.id,process='PROJEKT',machine_id=None).order_by(TimeBooking.start_time.desc()).limit(100).all(),
        parts=ToolPartEvent.query.filter_by(project_id=item.id).order_by(ToolPartEvent.id.desc()).limit(100).all(),reversed_ids={x.reverses_id for x in ToolPartEvent.query.filter_by(project_id=item.id) if x.reverses_id},
        selected_tool=selected_tool,tools=Tool.query.order_by(Tool.tool_no).all(),audits=Audit.query.filter_by(project_id=item.id).order_by(Audit.id.desc()).limit(50).all())

@bp.route('/sources')
@login_required
@permission_required('projects.work')
def sources():
    if not permitted('view'):abort(403)
    project(request.args.get('project_id',type=int) or 0,write=True)
    q=request.args.get('q','').strip()[:100];kind=request.args.get('kind');results=[]
    if len(q)<2:return jsonify(results=[])
    like='%'+q+'%'
    if kind=='sampling' and has_permission(current_user,'sampling.view'):
        for row in SamplingOrder.query.join(Order).filter(or_(Order.order_no.ilike(like),Order.tool_no.ilike(like),Order.article.ilike(like),Order.description.ilike(like))).limit(30):
            results.append({'id':row.id,'label':f'{row.order.order_no} · {row.order.tool_no or "Ohne Werkzeug"} · {row.state}'})
    elif kind=='error' and has_permission(current_user,'tool_error.view'):
        for row in ToolError.query.join(Tool).filter(or_(ToolError.error_no.ilike(like),ToolError.description.ilike(like),Tool.tool_no.ilike(like))).order_by(ToolError.id.desc()).limit(30):
            results.append({'id':row.id,'label':f'{row.error_no} · Revision {row.revision} · {row.tool.tool_no}'})
    else:abort(403)
    return jsonify(results=results)

@bp.route('/<int:project_id>/action',methods=['POST'])
@login_required
@permission_required('projects.view')
def action(project_id):
    csrf();written=[]
    try:
        lock();op=request.form.get('op');management=op in ('member','task_add','archive','reopen','settings')
        if not permitted('manage' if management else 'work'):abort(403)
        item=project(project_id,write=True,manage=management,allow_closed=op=='reopen');version(item,request.form.get('version'))
        data=request.form
        link_id=selected_link(item,data)
        if op=='member':
            user=User.query.get_or_404(data.get('user_id',type=int) or 0)
            if not user.active:raise ValueError('Nur aktive Mitarbeiter zuordnen.')
            key=(item.id,user.id)
            if data.get('remove')=='yes':
                if item.project_leader_id==user.id:raise ValueError('Projektleitung zuerst in den Einstellungen ändern.')
                if WorkTime.query.filter_by(project_id=item.id,user_id=user.id,ended_at=None,cancelled=False).first() or Task.query.filter(Task.project_id==item.id,Task.assignee_id==user.id,Task.status!='done').first():raise ValueError('Mitarbeiter hat laufende Zeiten oder offene Aufgaben.')
                existing=db.session.get(Member,key)
                if existing:db.session.delete(existing)
            elif not db.session.get(Member,key):db.session.add(Member(project_id=item.id,user_id=user.id))
            audit(item,'Mitarbeiterzuordnung',{'user_id':user.id,'remove':data.get('remove')=='yes'})
        elif op=='settings':
            leader=User.query.get_or_404(data.get('leader_id',type=int) or 0)
            if not leader.active:raise ValueError('Aktive Projektleitung erforderlich.')
            before={'description':item.description,'leader':item.project_leader_id}
            item.description=required(data,'description',255);item.project_leader_id=leader.id
            if not db.session.get(Member,(item.id,leader.id)):db.session.add(Member(project_id=item.id,user_id=leader.id))
            audit(item,'Projekteinstellungen',{'before':before,'description':item.description,'leader':leader.id})
        elif op=='task_add':
            assignee=data.get('assignee_id',type=int)
            if assignee not in members(item):raise ValueError('Aufgabe nur einem Projektmitglied zuweisen.')
            if not db.session.get(User,assignee).active:raise ValueError('Nur aktive Mitarbeiter einer Aufgabe zuweisen.')
            due=date.fromisoformat(data['due_date']) if data.get('due_date') else None
            task=Task(project_id=item.id,title=required(data,'title',200),assignee_id=assignee,due_date=due);db.session.add(task)
            audit(item,'Aufgabe angelegt',{'title':task.title,'assignee':assignee,'due':str(due)})
        elif op=='task_status':
            task=Task.query.filter_by(id=data.get('task_id',type=int),project_id=item.id).first_or_404()
            if task.assignee_id!=current_user.id and not permitted('manage'):abort(403)
            if data.get('status') not in TASK_STATES:raise ValueError('Ungültiger Aufgabenstatus.')
            audit(item,'Aufgabenstatus',{'id':task.id,'before':task.status,'after':data['status']});task.status=data['status']
        elif op=='link':
            kind=data.get('kind');target=data.get('target_id',type=int)
            if kind=='sampling' and has_permission(current_user,'sampling.view'):
                source=SamplingOrder.query.get_or_404(target or 0);link=Link(project_id=item.id,sampling_id=source.id);tool_no=source.order.tool_no
            elif kind=='error' and has_permission(current_user,'tool_error.view'):
                source=ToolError.query.get_or_404(target or 0);link=Link(project_id=item.id,error_id=source.id);tool_no=source.tool.tool_no
            else:abort(403)
            if item.tool_no and tool_no and item.tool_no!=tool_no and data.get('confirm_other_tool')!='yes':raise ValueError('Der Vorgang betrifft ein anderes Werkzeug. Zuordnung ausdrücklich bestätigen.')
            db.session.add(link);audit(item,'Vorgang verknüpft',{'kind':kind,'target':target,'other_tool_confirmed':data.get('confirm_other_tool')=='yes'})
        elif op=='report':
            report=Report(project_id=item.id,user_id=current_user.id,text=required(data,'text',5000),link_id=link_id);db.session.add(report);db.session.flush()
            files=[f for key in ('camera','photo') for f in request.files.getlist(key) if f.filename]
            if len(files)>5:raise ValueError('Maximal fünf Fotos je Arbeitsbericht.')
            prepared=[prepare_photo(f.stream) for f in files]
            folder=storage_root()/'Projects'/'Reports';folder.mkdir(parents=True,exist_ok=True)
            for encoded in prepared:
                filename=uuid4().hex+'.jpg';path=folder/filename;written.append(path);path.write_bytes(encoded);db.session.add(ReportPhoto(report_id=report.id,filename=filename))
            audit(item,'Arbeitsbericht',{'report_id':report.id,'photos':len(prepared)})
        elif op in ('time_start','time_manual'):
            start=datetime.utcnow() if op=='time_start' else local_time(data.get('start'),data.get('start_fold'))
            end=None if op=='time_start' else local_time(data.get('end'),data.get('end_fold'))
            check_interval(current_user.id,start,end)
            entry=WorkTime(project_id=item.id,user_id=current_user.id,started_at=start,ended_at=end,description=required(data,'description'),link_id=link_id)
            db.session.add(entry);audit(item,'Arbeitszeit erfasst',{'start':start.isoformat(),'end':end.isoformat() if end else None,'description':entry.description})
        elif op in ('time_stop','time_edit','time_cancel'):
            entry=WorkTime.query.filter_by(id=data.get('time_id',type=int),project_id=item.id).first_or_404()
            if entry.user_id!=current_user.id and not permitted('correct_times'):abort(403)
            if entry.cancelled:raise ValueError('Zeit wurde bereits storniert.')
            before={'id':entry.id,'start':entry.started_at.isoformat(),'end':entry.ended_at.isoformat() if entry.ended_at else None,'description':entry.description}
            if op=='time_stop':
                if entry.ended_at:raise ValueError('Zeit ist bereits beendet.')
                entry.ended_at=datetime.utcnow()
                if entry.ended_at<=entry.started_at:raise ValueError('Ende liegt nicht nach Start.')
            else:
                if not permitted('correct_times'):abort(403)
                reason=required(data,'reason')
                if op=='time_cancel':entry.cancelled=True
                else:
                    start=local_time(data.get('start'),data.get('start_fold'));end=local_time(data.get('end'),data.get('end_fold')) if data.get('end') else None
                    check_interval(entry.user_id,start,end,entry.id);entry.started_at=start;entry.ended_at=end;entry.description=required(data,'description')
                before['reason']=reason
            audit(item,op,{'before':before,'after':{'start':entry.started_at.isoformat(),'end':entry.ended_at.isoformat() if entry.ended_at else None,'cancelled':entry.cancelled,'description':entry.description}})
        elif op=='part':
            tool=Tool.query.get_or_404(data.get('tool_id',type=int) or 0)
            if data.get('operation') not in ('install','remove'):raise ValueError('Einbau oder Ausbau auswählen.')
            if data.get('confirmed')!='yes':raise ValueError('Tatsächlich durchgeführten Ein-/Ausbau bestätigen.')
            occurred=local_time(data.get('occurred_at'),data.get('start_fold'))
            if occurred>datetime.utcnow():raise ValueError('Ein-/Ausbau darf nicht in der Zukunft liegen.')
            if item.tool_no and item.tool_no!=tool.tool_no and data.get('confirm_other_tool')!='yes':raise ValueError('Abweichendes Werkzeug ausdrücklich bestätigen.')
            if link_id:
                linked=db.session.get(Link,link_id)
                source_tool=linked.sampling.order.tool_no if linked.sampling else linked.error.tool.tool_no
                if source_tool and source_tool!=tool.tool_no and data.get('confirm_other_tool')!='yes':raise ValueError('Werkzeug weicht vom zugeordneten Vorgang ab. Abweichung ausdrücklich bestätigen.')
            event=ToolPartEvent(project_id=item.id,tool_id=tool.id,user_id=current_user.id,operation=data['operation'],part_name=required(data,'part_name',200),part_no=data.get('part_no','').strip()[:100],serial_no=data.get('serial_no','').strip()[:100],position=required(data,'position',200),quantity=quantity(data.get('quantity')),unit=required(data,'unit',20),reason=required(data,'reason'),disposition=data.get('disposition','').strip()[:200],occurred_at=occurred)
            event.link_id=link_id
            db.session.add(event);db.session.flush();audit(item,'Werkzeugteil dokumentiert',{'event_id':event.id,'tool':tool.tool_no,'operation':event.operation,'part':event.part_name,'quantity':str(event.quantity),'position':event.position})
        elif op=='part_reverse':
            if not permitted('manage'):abort(403)
            event=ToolPartEvent.query.filter_by(id=data.get('event_id',type=int),project_id=item.id).first_or_404()
            if event.reverses_id or ToolPartEvent.query.filter_by(reverses_id=event.id).first():raise ValueError('Eintrag wurde bereits storniert oder ist selbst ein Storno.')
            reason=required(data,'reason')
            db.session.add(ToolPartEvent(project_id=item.id,tool_id=event.tool_id,user_id=current_user.id,operation='correction',part_name=event.part_name,part_no=event.part_no,serial_no=event.serial_no,position=event.position,quantity=event.quantity,unit=event.unit,reason=reason,occurred_at=datetime.utcnow(),reverses_id=event.id))
            audit(item,'Teileintrag storniert',{'event_id':event.id,'reason':reason})
        elif op in ('archive','reopen'):
            reason=required(data,'reason')
            if op=='archive':
                if WorkTime.query.filter_by(project_id=item.id,ended_at=None,cancelled=False).first() or TimeBooking.query.filter_by(order_id=item.id,process='PROJEKT',end_time=None).first():raise ValueError('Laufende Mitarbeiterzeiten zuerst beenden.')
                if Task.query.filter(Task.project_id==item.id,Task.status!='done').first():raise ValueError('Offene Aufgaben zuerst abschließen.')
            audit(item,op,{'before':item.status,'reason':reason});item.status='fertig' if op=='archive' else 'offen'
        else:raise ValueError('Unbekannte Aktion.')
        item.updated_at=datetime.utcnow();db.session.commit()
        return redirect(url_for('projects.detail',project_id=item.id),303)
    except ValueError as error:
        for path in written:path.unlink(missing_ok=True)
        return failed(error,project_id)
    except (IntegrityError,OperationalError):
        for path in written:path.unlink(missing_ok=True)
        return failed('Aktion bereits verarbeitet, gleichzeitige Änderung oder Datenbank beschäftigt. Bitte neu laden und prüfen.',project_id,409)
    except Exception:
        db.session.rollback()
        for path in written:path.unlink(missing_ok=True)
        raise

@bp.route('/photo/<int:photo_id>')
@login_required
@permission_required('projects.view')
def report_photo(photo_id):
    photo=ReportPhoto.query.get_or_404(photo_id);project(photo.report.project_id)
    response=send_file(storage_root()/'Projects'/'Reports'/photo.filename,mimetype='image/jpeg');response.headers['Cache-Control']='private, no-store';response.headers['X-Content-Type-Options']='nosniff';return response

@bp.route('/tool/<int:tool_id>/history')
@login_required
@permission_required('projects.view')
def tool_history(tool_id):
    if not has_permission(current_user,'tools.view'):abort(403)
    tool=Tool.query.get_or_404(tool_id)
    visible=Order.query.filter(Order.is_project.is_(True))
    if not permitted('view_all'):visible=visible.filter(mine_clause())
    events=ToolPartEvent.query.filter(ToolPartEvent.tool_id==tool.id,ToolPartEvent.project_id.in_(db.select(visible.subquery().c.id))).order_by(ToolPartEvent.occurred_at.desc()).limit(300).all()
    reversed_ids={x.reverses_id for x in ToolPartEvent.query.filter(ToolPartEvent.tool_id==tool.id,ToolPartEvent.reverses_id.isnot(None))}
    return render_template('projects/workspace_tool.html',tool=tool,parts=events,reversed_ids=reversed_ids,fmt=berlin)

# Preserve historical links without permitting them to bypass workspace access.
@bp.route('/start/<int:order_id>',methods=['POST'])
@login_required
@permission_required('projects.work')
def projects_start(order_id):
    csrf();project(order_id,write=True);flash('Bitte Arbeitszeit auf der Projektseite starten.','info');return redirect(url_for('projects.detail',project_id=order_id),303)

@bp.route('/stop/<int:booking_id>',methods=['GET','POST'])
@login_required
@permission_required('projects.work')
def projects_stop(booking_id):
    entry=TimeBooking.query.get_or_404(booking_id)
    if entry.user_id!=current_user.id or entry.process!='PROJEKT' or entry.machine_id is not None:abort(403)
    project(entry.order_id)
    if request.method=='POST':
        csrf();lock()
        if entry.end_time is not None:return failed('Altbuchung wurde bereits beendet.',entry.order_id,409)
        entry.end_time=datetime.utcnow();audit(entry.order,'Alt-Projektzeit beendet',{'booking':entry.id});db.session.commit();return redirect(url_for('projects.detail',project_id=entry.order_id),303)
    return render_template('projects/workspace_legacy.html',entry=entry,fmt=berlin)
