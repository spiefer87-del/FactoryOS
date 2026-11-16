"""Read-only, master-backed tool proposals and visible sampling prerequisites."""
from factoryos.extensions import db
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.masterdata.articles.models import Article
from ..models import TimeBooking,ProductionPlanEntry

SAMPLING_STATES={'draft':'Entwurf','rework':'Nacharbeit','in_progress':'In Bearbeitung','review':'In Prüfung'}


def sampling_ready(order,machine_id):
    return bool(order.sampling and order.sampling.state in ('in_progress','review') and order.sampling.machine_id==machine_id
                and (order.status or '').lower() not in ('gesperrt','locked'))


def visible_order(order,machine_id):
    if order.is_project or order.completion:return False
    status=(order.status or '').lower()
    if order.sampling:
        return (order.sampling.state in SAMPLING_STATES
                and status not in ('fertig','finished','abgeschlossen','cancelled','canceled','storniert'))
    from .machine_control_service import TERMINAL
    return status not in TERMINAL


def tool_proposal(order,tools):
    if not order:return None
    if order.sampling and order.sampling.tool:
        number=order.sampling.tool.tool_no;source='Werkzeugstamm des Musterungsauftrags'
    elif order.tool_no:
        number=order.tool_no;source='Gespeichertes Werkzeug des Auftrags'
    else:
        article=Article.query.filter_by(article_no=order.article or '').first()
        if not article or len(article.tools)!=1:return None
        number=article.tools[0].tool_no;source='Eindeutige Werkzeugzuordnung im Artikelstamm'
    tool=tools.get(number)
    return dict(number=tool.tool_no,name=tool.name or '',source=source) if tool else None


def stock_proposal(machine_id,mount,tools):
    if mount['status']=='empty':return None
    number=mount.get('tool_no')
    source='Bestätigter montierter Bestand' if mount['status']=='mounted' else 'Zuletzt gespeicherter Werkzeugbezug – vor Ort prüfen'
    if not number:
        last=TimeBooking.query.filter(TimeBooking.machine_id==machine_id,TimeBooking.tool_no.isnot(None),
            TimeBooking.tool_no!='').order_by(TimeBooking.start_time.desc(),TimeBooking.id.desc()).first()
        number=last.tool_no if last else None
        source='Letzte Werkzeugbuchung dieser Maschine – noch keine Montagebestätigung'
    tool=tools.get(number)
    return dict(number=tool.tool_no,name=tool.name or '',source=source) if tool else None


def validate_tool_choice(action,form):
    if action not in ('start','setup','unsetup'):return
    number=(form.get('tool_no') or '').strip()
    if not number:raise ValueError('Werkzeugnummer: vorhandenes Werkzeug auswählen oder eingeben und bestätigen.')
    if not Tool.query.filter_by(tool_no=number).first():raise ValueError('Werkzeugnummer: diese Nummer ist nicht im Werkzeugstamm vorhanden. Bitte einen gültigen Eintrag auswählen.')
    if form.get('tool_confirmed')!='yes' or (form.get('tool_confirmation_no') or '').strip()!=number:
        raise ValueError('Werkzeugnummer '+number+': bitte den Haken „Werkzeug geprüft“ für genau diese Nummer setzen. Änderungen erfordern eine neue Bestätigung.')


def prepare_sampling(machine_id,sampling_id,user_id,version,revision,*,change_confirmed=False):
    """Explicit preparation only: no booking, no automatic production/QM release."""
    import copy
    from factoryos.models.user import User
    from factoryos.models.machine import Machine
    from factoryos.modules.sampling.models import SamplingOrder
    from factoryos.core.auth import has_permission
    from factoryos.core.services.change_log_service import log_change
    from .machine_control_service import acquire_control_lock,snapshot,current_booking,ControlConflict,ControlDenied
    acquire_control_lock();user=db.session.get(User,user_id)
    if not has_permission(user,'sampling.edit') or not has_permission(user,'production.view'):raise ControlDenied('Musterung vorbereiten benötigt „Musterungsaufträge bearbeiten“ und „Produktion ansehen“.')
    machine=db.session.get(Machine,machine_id);record=db.session.get(SamplingOrder,sampling_id)
    if not machine or machine.machine_status!='aktiv':raise ValueError('Bitte eine aktive Maschine auswählen.')
    if not record or not visible_order(record.order,machine_id):raise ControlConflict('Musterung ist abgeschlossen oder storniert.')
    if record.machine_id not in (None,machine_id) and not change_confirmed:
        raise ValueError('Musterung ist für '+record.machine.machine_no+' vorgesehen. Wechsel auf '+machine.machine_no+' bitte mit dem zusätzlichen Haken ausdrücklich bestätigen.')
    if str(record.version)!=str(version) or snapshot(machine_id)['revision']!=revision:raise ControlConflict('Musterung oder Maschinenstand geändert. Bitte neu laden und erneut prüfen.')
    planned=ProductionPlanEntry.query.filter_by(order_id=record.order_id,state='queued').first()
    if planned and planned.machine_id!=machine_id:raise ControlConflict('Musterung steht noch in der Warteschlange von '+planned.machine.machine_no+'. Bitte zuerst regulär in der Auftragsplanung umplanen; eine Bestätigung verschiebt keine fremde Warteschlange.')
    if sampling_ready(record.order,machine_id):raise ControlConflict('Musterung ist für diese Maschine bereits in Bearbeitung/Prüfung. Bitte zur Bedienung zurückkehren; keine erneute Übernahme nötig.')
    if record.state in ('in_progress','review') and (record.order.status or '').lower() in ('gesperrt','locked'):
        raise ValueError('Musterungsauftrag ist gesperrt. Sperre bitte in der regulären Auftragsbearbeitung prüfen, nicht über die Maschinenvorbereitung umgehen.')
    active=current_booking(machine_id)
    if len(snapshot(machine_id)['active'])>1 or (active and active.process!='FREI'):raise ControlConflict('Maschine ist bereits in einem Vorgang. Diesen zuerst regulär beenden.')
    from .machine_control_service import _order
    # Check quantity/cycle and reservations without bypassing the sampling gate:
    # tentative state is only committed if every regular validation succeeds.
    old=dict(state=record.state,machine_id=record.machine_id,status=record.order.status,snapshot=copy.deepcopy(record.snapshot))
    record.machine=machine
    record.machine_id=machine.id
    if record.state in ('draft','rework'):record.state='in_progress'
    record.order.status='in_arbeit'
    if not record.tool or not Tool.query.filter_by(id=record.tool_id).first():raise ValueError('Musterungsauftrag: Werkzeug im Stamm ergänzen und im Musterungsauftrag zuordnen.')
    if record.order.tool_no and record.order.tool_no!=record.tool.tool_no:raise ValueError('Werkzeugzuordnung im Musterungsauftrag widerspricht dem gespeicherten Auftragswerkzeug. Bitte zuerst korrigieren.')
    record.order.tool_no=record.tool.tool_no
    _order(record.order_id,machine_id)
    reference=copy.deepcopy(record.snapshot or {});reference['machine']=dict(number=machine.machine_no,name=machine.name or '')
    record.snapshot=reference
    db.session.flush()
    changes={'machine_preparation':{'old':old,'new':dict(state=record.state,machine_id=record.machine_id,status=record.order.status,
        tool_no=record.tool.tool_no,note='Bewusst vorbereitet; keine Produktionsbuchung und keine Prüffreigabe')}}
    log_change('sampling',record.id,'update',entity_name=record.order.order_no,category='sampling_preparation',changes=changes)
    log_change('order',record.order_id,'update',entity_name=record.order.order_no,category='sampling_preparation',changes=changes)
    db.session.commit();return record
