from uuid import uuid4
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from factoryos.extensions import db
from factoryos.core.auth import permission_required, has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.models.machine import Machine
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import DowntimeReason, MachineControlCommand
from factoryos.modules.production.services.machine_control_service import (
    execute, snapshot, current_booking, available_actions, ACTIONS, LABELS, PERMISSIONS,
    TERMINAL, ControlConflict, ControlDenied,
)
from factoryos.modules.production.services.order_statistics import local_label
from . import bp
from factoryos.modules.production.services.control_selection_service import (
    visible_order,sampling_ready,tool_proposal,stock_proposal,validate_tool_choice,SAMPLING_STATES)


@bp.route("/machine/<int:machine_id>/control",methods=["GET","POST"])
@login_required
@permission_required("production.view")
def machine_control(machine_id):
    machine=Machine.query.get_or_404(machine_id)
    embedded=request.args.get("embedded")=="1"
    error=None;status=200
    if request.method=="POST":
        if not valid_csrf(): abort(400,"Formular abgelaufen. Bitte neu laden.")
        action=request.form.get('action')
        if action in PERMISSIONS and not has_permission(current_user,PERMISSIONS[action]):abort(403)
        if action in ('record_wait','finish_setup'):
            active=current_booking(machine_id)
            if action=='record_wait' or (active and active.process in ('RUEST','ABRUEST')):
                endpoint='production.teardown_finish' if action=='finish_setup' and active.process=='ABRUEST' else 'production.setup_finish'
                return redirect(url_for(endpoint,machine_id=machine_id,
                    wait='1' if action=='record_wait' else None,embedded='1' if embedded else None,
                    revision=request.form.get('revision','')),303)
        if request.form.get("action")=="fault":
            if not has_permission(current_user,PERMISSIONS["fault"]): abort(403)
            # Old clients may still submit the former button. Navigation only:
            # a fault is now confirmed exclusively on its own selection page.
            return redirect(url_for("production.machine_fault",machine_id=machine_id,
                embedded="1" if embedded else None,revision=request.form.get("revision","")),code=303)
        try:
            if action not in ('preview_selection','preview_tool','preview_stock'):
                validate_tool_choice(action,request.form)
                if action in ('start','setup') and request.form.get('order_id'):
                    selected=Order.query.get(request.form.get('order_id',type=int))
                    if selected and selected.sampling and not sampling_ready(selected,machine_id):
                        raise ValueError('Musterungsauftrag zuerst bewusst vorbereiten: Bearbeitungsstatus und Maschinenzuordnung prüfen. Der Vorbereitungslink steht unter der Auftragsauswahl.')
                _,replayed=execute(machine_id,current_user.id,action,
                    request.form.get("command_id"),request.form.get("revision"),
                    order_id=None if action=='unsetup' else request.form.get("order_id"),tool_no=request.form.get("tool_no"),
                    reason_id=request.form.get("reason_id"),comment=request.form.get("comment",""))
                flash("Befehl war bereits verarbeitet – keine Doppelbuchung." if replayed else "Maschinenzustand gespeichert.","success")
                return redirect(url_for("production.machine_control",machine_id=machine_id,
                    embedded="1" if embedded else None,changed="1"),code=303)
        except ControlDenied as exc:
            db.session.rollback();abort(403,str(exc))
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:
            db.session.rollback();error="Maschine wurde parallel geändert oder Datenbank ist belegt. Bitte neu laden und prüfen.";status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    from factoryos.modules.production.services.idle_context_service import idle_views
    idle=idle_views([active]).get(active.id) if active else None
    process=active.process if active else "FREI"
    conflict=len(state["active"])>1
    actions=available_actions(process)
    if 'record_wait' in actions and state['tool_mount']['status']!='mounted':actions.remove('record_wait')
    permitted={action:has_permission(current_user,PERMISSIONS[action]) for action in ACTIONS}
    resume=state["resume_process"]
    if resume in ("RUEST","ABRUEST"): permitted["resume"] &= has_permission(current_user,"production.setup")
    elif resume=="WARTUNG": permitted["resume"] &= has_permission(current_user,"production.maintenance")
    elif resume=="SONSTIG": permitted["resume"] &= has_permission(current_user,"production.events")
    else: permitted["resume"] &= has_permission(current_user,"production.start")
    orders=Order.query.filter_by(is_project=False).order_by(Order.order_no).all()
    orders=[o for o in orders if visible_order(o,machine_id)]
    from factoryos.modules.production.services.planning_service import queue
    from factoryos.modules.production.models import ProductionPlanEntry
    planned_queue=queue(machine_id)
    from factoryos.modules.production.services.tool_mount_service import tool_label,operation_times
    from factoryos.modules.production.models import SetupOperation,MachineToolState
    assignments={e.order_id:e.machine_id for e in ProductionPlanEntry.query.filter_by(state="queued")}
    orders=[o for o in orders if o.sampling or o.id not in assignments or assignments[o.id]==machine_id]
    machine_names={m.id:m.machine_no for m in Machine.query.all()}
    tools=Tool.query.order_by(Tool.tool_no).all();tool_map={t.tool_no:t for t in tools}
    stock=stock_proposal(machine_id,state['tool_mount'],tool_map)
    catalog={}
    for order in orders:
        sampling=order.sampling
        note=('Musterung · '+SAMPLING_STATES.get(sampling.state,sampling.state)) if sampling else 'Fertigungsauftrag'
        if sampling and sampling.machine_id not in (None,machine_id):note+=' · ⚠ Für '+machine_names.get(sampling.machine_id,'andere Maschine')+' vorgesehen – Wechsel bestätigen'
        elif sampling and not sampling.machine_id:note+=' · Maschine noch nicht zugeordnet'
        if sampling and assignments.get(order.id) not in (None,machine_id):note+=' · Warteschlange auf '+machine_names.get(assignments[order.id],'anderer Maschine')+' – zuerst in Planung umplanen'
        if sampling and sampling.state in ('in_progress','review') and (order.status or '').lower() in ('gesperrt','locked'):note+=' · Auftrag gesperrt – regulär prüfen'
        catalog[str(order.id)]=dict(proposal=tool_proposal(order,tool_map),sampling=bool(sampling),
            ready=(sampling_ready(order,machine_id) and assignments.get(order.id) in (None,machine_id)) if sampling else True,
            note=note,
            prepare_url=url_for('production.prepare_sampling',machine_id=machine_id,sampling_id=sampling.id,embedded='1' if embedded else None) if sampling and has_permission(current_user,'sampling.edit') else None)
    selected_order=request.form.get('order_id',request.args.get('order_id',str(active.order_id) if active and process=='FREI' and active.order_id else str(planned_queue[0].order_id) if planned_queue else ''))
    selected_info=catalog.get(str(selected_order),{})
    proposal=selected_info.get('proposal') or stock
    if request.form.get('action')=='preview_stock':proposal=stock
    selected_tool=(proposal['number'] if proposal else '') if request.form.get('action') in ('preview_selection','preview_stock') else request.form.get('tool_no',proposal['number'] if proposal else '')
    response=render_template("production/control/panel.html",machine=machine,state=state,active=active,
        process=process,actions=actions,action_labels=ACTIONS,labels=LABELS,permitted=permitted,
        tool_mount=state['tool_mount'],tool_mount_label=tool_label(state['tool_mount']),
        tool_mount_record=db.session.get(MachineToolState,machine_id),
        idle=idle,
        setup_history=SetupOperation.query.filter_by(machine_id=machine_id).order_by(SetupOperation.id.desc()).limit(30).all(),
        operation_times=operation_times,
        conflict=conflict,error=error,orders=orders,
        tools=tools,selection_data=dict(orders=catalog,stock=stock,tools=[dict(number=t.tool_no,name=t.name or '') for t in tools]),
        selected_info=selected_info,proposal=proposal,stock_proposal=stock,
        history=MachineControlCommand.query.filter_by(machine_id=machine_id).order_by(MachineControlCommand.id.desc()).limit(30).all(),
        embedded=embedded,command_id=str(uuid4()),local_label=local_label,planned_queue=planned_queue,
        selected_order=selected_order,selected_tool=selected_tool,
        comment=request.form.get("comment", ""))
    return response,status,{"Cache-Control":"no-store","X-Frame-Options":"SAMEORIGIN"}


@bp.route('/machine/<int:machine_id>/control/stop',methods=['GET','POST'])
@login_required
@permission_required('production.view')
def machine_stop(machine_id):
    machine=Machine.query.get_or_404(machine_id);embedded=request.args.get('embedded')=='1'
    error=None;status=200
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        try:
            execute(machine_id,current_user.id,'stop',request.form.get('command_id'),request.form.get('revision'),comment=request.form.get('comment',''))
            flash('Vorgang gestoppt. Der Auftrag bleibt offen.','success')
            return redirect(url_for('production.machine_control',machine_id=machine_id,embedded='1' if embedded else None,changed='1'),303)
        except ControlDenied as exc:db.session.rollback();abort(403,str(exc))
        except ValueError as exc:db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:db.session.rollback();error='Maschinenstand wurde parallel geändert. Bitte neu laden.';status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    expected=request.form.get('revision','') if request.method=='POST' else request.args.get('revision',state['revision'])
    blocked=len(state['active'])>1 or expected!=state['revision'] or 'stop' not in available_actions(active.process if active else 'FREI')
    if blocked:error='Maschinenstand passt nicht mehr. Bitte zur Maschinenbedienung zurückkehren und neu laden.';status=409
    response=render_template('production/control/stop.html',machine=machine,active=active,embedded=embedded,
        has_open_setup=bool(state['tool_mount']['operation']),
        error=error,blocked=blocked,expected_revision=expected,command_id=str(uuid4()),
        can_stop=has_permission(current_user,'production.stop'),
        can_complete=has_permission(current_user,'production.complete_order') and active and active.order and not active.order.sampling and active.process in ('PROD','PAUSE'))
    return response,status,{'Cache-Control':'no-store','X-Frame-Options':'SAMEORIGIN'}


@bp.route('/machine/<int:machine_id>/control/complete-order',methods=['GET','POST'])
@login_required
@permission_required('production.complete_order')
def machine_complete_order(machine_id):
    if not has_permission(current_user,'production.view'):abort(403)
    machine=Machine.query.get_or_404(machine_id);active=current_booking(machine_id)
    order_id=request.form.get('order_id',type=int) if request.method=='POST' else active.order_id if active else None
    if not order_id:abort(409,'Kein aktiver Auftrag auf dieser Maschine. Bitte neu laden.')
    if request.method=='POST' and (not active or active.order_id!=order_id):
        from factoryos.modules.production.models import OrderCompletion
        receipt=OrderCompletion.query.filter_by(command_id=request.form.get('command_id'),order_id=order_id,
            machine_id=machine.id,user_id=current_user.id,source='machine').first()
        if not receipt:abort(409,'Auftragszuordnung an der Maschine wurde geändert. Bitte neu laden.')
    from factoryos.modules.orders.routes.completion_routes import completion_page
    return completion_page(Order.query.get_or_404(order_id),'machine',machine=machine,embedded=request.args.get('embedded')=='1')


@bp.route("/machine/<int:machine_id>/control/fault",methods=["GET","POST"])
@login_required
@permission_required("production.view")
@permission_required("production.stop")
def machine_fault(machine_id):
    machine=Machine.query.get_or_404(machine_id)
    embedded=request.args.get("embedded")=="1"
    error=None;status=200
    if request.method=="POST":
        if not valid_csrf(): abort(400,"Formular abgelaufen. Bitte neu laden.")
        try:
            _,replayed=execute(machine_id,current_user.id,"fault",
                request.form.get("command_id"),request.form.get("revision"),
                reason_id=request.form.get("reason_id"),comment=request.form.get("comment",""))
            flash("Störung war bereits gespeichert – keine Doppelbuchung." if replayed else "Störung gespeichert.","success")
            return redirect(url_for("production.machine_control",machine_id=machine_id,
                embedded="1" if embedded else None,changed="1"),code=303)
        except ControlDenied as exc:
            db.session.rollback();abort(403,str(exc))
        except ValueError as exc:
            db.session.rollback();error=str(exc);status=409 if isinstance(exc,ControlConflict) else 400
        except SQLAlchemyError:
            db.session.rollback();error="Maschinenstand wurde parallel geändert oder Datenbank ist belegt. Bitte neu laden und prüfen.";status=409
    state=snapshot(machine_id);active=current_booking(machine_id)
    process=active.process if active else "FREI"
    expected=request.form.get("revision","") if request.method=="POST" else request.args.get("revision",state["revision"])
    blocked=(len(state["active"])>1 or "fault" not in available_actions(process) or expected!=state["revision"])
    if blocked:
        error="Der Maschinenstand ist nicht mehr für diese Störmeldung gültig. Bitte neu laden und den aktuellen Zustand prüfen."
        status=409
    response=render_template("production/control/fault.html",machine=machine,state=state,active=active,
        process=process,labels=LABELS,embedded=embedded,error=error,blocked=blocked,
        expected_revision=expected,command_id=str(uuid4()),local_label=local_label,
        reasons=DowntimeReason.query.filter_by(active=True).order_by(DowntimeReason.name).all(),
        selected_reason=request.form.get("reason_id",""),comment=request.form.get("comment",""))
    return response,status,{"Cache-Control":"no-store","X-Frame-Options":"SAMEORIGIN"}


@bp.route("/machine/<int:machine_id>/control/state")
@login_required
@permission_required("production.view")
def machine_control_state(machine_id):
    Machine.query.get_or_404(machine_id)
    state=snapshot(machine_id)
    from factoryos.modules.production.services.idle_context_service import idle_views
    active=current_booking(machine_id);info=idle_views([active]).get(active.id) if active else None
    return jsonify(revision=state["revision"],wait_hint=info['hint'] if info else ''),200,{"Cache-Control":"no-store"}
