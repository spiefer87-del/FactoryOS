"""Human-readable views of the existing, immutable project audit records."""
from datetime import datetime, timezone
from types import SimpleNamespace

from flask_login import current_user
from sqlalchemy.orm import joinedload

from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from factoryos.modules.sampling.models import SamplingOrder
from factoryos.modules.tool_errors.models import ToolError
from ..definitions import PROJECT_TYPES
from ..workspace_models import Task, ToolPartEvent
from .workspace_service import berlin

ACTION_LABELS = {
    'Projekt angelegt': 'Projekt angelegt',
    'Projekteinstellungen': 'Projekteinstellungen geändert',
    'Mitarbeiterzuordnung': 'Projektteam geändert',
    'Aufgabe angelegt': 'Aufgabe angelegt',
    'Aufgabenstatus': 'Aufgabenstatus geändert',
    'Vorgang verknüpft': 'Vorgang verknüpft',
    'Arbeitsbericht': 'Arbeitsbericht ergänzt',
    'Arbeitszeit erfasst': 'Arbeitszeit erfasst',
    'time_stop': 'Arbeitszeit beendet / pausiert',
    'time_edit': 'Arbeitszeit korrigiert',
    'time_cancel': 'Arbeitszeit storniert',
    'Werkzeugteil dokumentiert': 'Werkzeugteil dokumentiert',
    'Teileintrag storniert': 'Teileintrag storniert',
    'archive': 'Projekt archiviert',
    'reopen': 'Projekt wieder geöffnet',
    'Alt-Projektzeit beendet': 'Bisherige Projektzeit beendet',
}
TASK_LABELS = {'open': 'Offen', 'working': 'In Arbeit', 'waiting': 'Wartet',
               'feedback': 'Rückmeldung offen', 'done': 'Abgeschlossen'}
STATUS_LABELS = {'offen': 'Offen', 'open': 'Offen', 'running': 'In Arbeit',
                 'fertig': 'Archiviert', 'finished': 'Archiviert', 'closed': 'Archiviert',
                 'gesperrt': 'Gesperrt', 'locked': 'Gesperrt'}


def number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def text(value, empty='—'):
    return empty if value is None or value == '' else str(value)


def timestamp(value, empty='Läuft'):
    if not value:
        return empty
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return berlin(parsed)
    except (TypeError, ValueError, OverflowError):
        return 'Zeitangabe nicht verfügbar'


def date_label(value):
    if not value or value == 'None':
        return 'Ohne Termin'
    try:
        return datetime.fromisoformat(str(value)).strftime('%d.%m.%Y')
    except (TypeError, ValueError):
        return 'Termin nicht verfügbar'


def present_audits(audits, project_names=None):
    """Resolve referenced names in batches, including records from older releases."""
    audits = list(audits)
    if not audits:
        return []
    user_ids = {a.user_id for a in audits}
    task_ids, event_ids, sampling_ids, error_ids = set(), set(), set(), set()
    for audit in audits:
        data = audit.data if isinstance(audit.data, dict) else {}
        for source in (data, data.get('before'), data.get('after')):
            if isinstance(source, dict):
                user_ids.update(number(source.get(key)) for key in ('leader', 'assignee', 'user_id'))
        if audit.action == 'Aufgabenstatus':
            task_ids.add(number(data.get('id')))
        if audit.action in ('Werkzeugteil dokumentiert', 'Teileintrag storniert'):
            event_ids.add(number(data.get('event_id')))
        if audit.action == 'Vorgang verknüpft':
            (sampling_ids if data.get('kind') == 'sampling' else error_ids).add(number(data.get('target')))
        if data.get('sampling_id'):
            sampling_ids.add(number(data['sampling_id']))

    def rows(model, ids, *options):
        ids = ids - {None}
        if not ids:
            return {}
        return {row.id: row for row in model.query.filter(model.id.in_(ids)).options(*options).all()}

    users = rows(User, user_ids)
    tasks = rows(Task, task_ids)
    events = rows(ToolPartEvent, event_ids)
    sampling_allowed = has_permission(current_user, 'sampling.view')
    errors_allowed = has_permission(current_user, 'tool_error.view')
    samplings = rows(SamplingOrder, sampling_ids, joinedload(SamplingOrder.order)) if sampling_allowed else {}
    errors = rows(ToolError, error_ids) if errors_allowed else {}
    if project_names is None:
        project_names = {p.id: p.order_no for p in Order.query.filter(Order.id.in_({a.project_id for a in audits})).all()}

    def username(value):
        user = users.get(number(value))
        return user.username if user else ('Nicht zugewiesen' if value is None else f'Mitarbeiter #{value}')

    def kind_label(value):
        return PROJECT_TYPES.get(value, {}).get('label', 'Nicht eingeordnet')

    def source_label(kind, key):
        if kind == 'sampling':
            source = samplings.get(number(key))
            if not sampling_allowed:
                return 'Geschützte Musterung'
            return source.order.order_no if source else f'Musterung #{key}'
        source = errors.get(number(key))
        if not errors_allowed:
            return 'Geschützte Fehlermeldung'
        return f'{source.error_no} · Revision {source.revision}' if source else f'Fehlermeldung #{key}'

    result = []
    for audit in audits:
        data = audit.data if isinstance(audit.data, dict) else {}
        before = data.get('before') if isinstance(data.get('before'), dict) else {}
        after = data.get('after') if isinstance(data.get('after'), dict) else {}
        lines = []

        def detail(label, value):
            lines.append(dict(label=label, value=text(value), changed=False))

        def change(label, old, new):
            if old != new:
                lines.append(dict(label=label, old=text(old), value=text(new), changed=True))

        action = audit.action
        if action == 'Projekt angelegt':
            for key, label, formatter in (
                ('description', 'Beschreibung / Ziel', text),
                ('project_kind', 'Projektgrund', kind_label),
                ('tool_no', 'Werkzeug', text),
            ):
                if key in data:
                    detail(label, formatter(data[key]))
            if data.get('sampling_id'):
                detail('Musterung', source_label('sampling', data['sampling_id']))
        elif action == 'Projekteinstellungen':
            for key, label, formatter in (
                ('description', 'Beschreibung / Ziel', text),
                ('leader', 'Projektleitung', username),
                ('project_kind', 'Projektgrund', kind_label),
                ('tool_no', 'Werkzeug', text),
            ):
                if key in before and key in data:
                    change(label, formatter(before[key]), formatter(data[key]))
                elif key in data:
                    detail(label, formatter(data[key]))
            if not lines:
                detail('Ergebnis', 'Gespeichert; keine inhaltliche Änderung')
        elif action == 'Mitarbeiterzuordnung':
            detail('Mitarbeiter', username(data.get('user_id')))
            detail('Zuordnung', 'Entfernt' if data.get('remove') else 'Zum Projekt hinzugefügt')
        elif action == 'Aufgabe angelegt':
            detail('Aufgabe', data.get('title'))
            detail('Zuständig', username(data.get('assignee')))
            detail('Termin', date_label(data.get('due')))
        elif action == 'Aufgabenstatus':
            task = tasks.get(number(data.get('id')))
            detail('Aufgabe', data.get('title') or (task.title if task else f"Aufgabe #{data.get('id')}"))
            change('Status', TASK_LABELS.get(data.get('before'), 'Unbekannt'), TASK_LABELS.get(data.get('after'), 'Unbekannt'))
        elif action == 'Vorgang verknüpft':
            kind = data.get('kind')
            detail('Musterung' if kind == 'sampling' else 'Fehlermeldung', source_label(kind, data.get('target')))
            if data.get('other_tool_confirmed'):
                detail('Abweichendes Werkzeug', 'Bewusst bestätigt')
        elif action == 'Arbeitsbericht':
            detail('Bericht', f"Arbeitsbericht #{data.get('report_id')}")
            detail('Fotos', data.get('photos', 0))
        elif action == 'Arbeitszeit erfasst':
            detail('Tätigkeit', data.get('description'))
            detail('Beginn', timestamp(data.get('start'), 'Nicht erfasst'))
            detail('Ende', timestamp(data.get('end')))
        elif action in ('time_stop', 'time_edit', 'time_cancel'):
            detail('Tätigkeit', before.get('description') or after.get('description'))
            for key, label, formatter in (
                ('start', 'Beginn', lambda v: timestamp(v, 'Nicht erfasst')),
                ('end', 'Ende', timestamp), ('description', 'Tätigkeit', text),
            ):
                if key in before and key in after:
                    change(label, formatter(before[key]), formatter(after[key]))
            if action == 'time_cancel':
                detail('Status', 'Storniert')
            if before.get('reason'):
                detail('Begründung', before['reason'])
        elif action in ('Werkzeugteil dokumentiert', 'Teileintrag storniert'):
            event = events.get(number(data.get('event_id')))
            if action == 'Werkzeugteil dokumentiert':
                detail('Werkzeug', data.get('tool'))
                detail('Vorgang', {'install': 'Einbau', 'remove': 'Ausbau'}.get(data.get('operation'), 'Teileintrag'))
                detail('Teil', data.get('part'))
                detail('Menge', text(data.get('quantity')) + (f' {event.unit}' if event else ''))
                detail('Position / Nest', data.get('position'))
            else:
                detail('Teil', event.part_name if event else f"Teileintrag #{data.get('event_id')}")
            reason = data.get('reason') or (event.reason if event else None)
            if reason:
                detail('Begründung', reason)
        elif action in ('archive', 'reopen'):
            change('Status', STATUS_LABELS.get(data.get('before'), text(data.get('before'))), 'Archiviert' if action == 'archive' else 'Offen')
            detail('Begründung / Abschlussbericht', data.get('reason'))
        elif action == 'Alt-Projektzeit beendet':
            detail('Buchung', f"Bisherige Projektzeit #{data.get('booking')}")
        else:
            detail('Hinweis', 'Älterer Projekteintrag ohne aufbereitete Detailangaben')

        result.append(SimpleNamespace(
            id=audit.id, entity_type='project', entity_id=audit.project_id,
            entity_name=project_names.get(audit.project_id, f'#{audit.project_id}'),
            created_at=audit.created_at, when=berlin(audit.created_at) if audit.created_at else 'Zeitpunkt nicht erfasst',
            user=users.get(audit.user_id), action=action,
            action_label=ACTION_LABELS.get(action, 'Projektänderung'), lines=lines,
            is_project_activity=True,
        ))
    return result
