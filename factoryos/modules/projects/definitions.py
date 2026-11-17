"""Project purpose controls the available workspace sections."""
PROJECT_TYPES = {
    'customer_request': dict(label='Kundenanfrage', hint='Anfrage, Machbarkeit und nächste Schritte mit dem Kunden klären.', parts=False, tool_required=False, sampling_required=False, links=('sampling',)),
    'tool_repair': dict(label='Werkzeugreparatur', hint='Befund, Reparatur und tatsächlich gewechselte Werkzeugteile dokumentieren.', parts=True, tool_required=True, sampling_required=False, links=('error', 'sampling')),
    'tool_maintenance': dict(label='Werkzeugwartung', hint='Wartungsarbeiten und durchgeführte Teilewechsel dokumentieren.', parts=True, tool_required=True, sampling_required=False, links=('error', 'sampling')),
    'tool_change': dict(label='Werkzeugänderung', hint='Änderungen am Werkzeug und eine gegebenenfalls folgende Musterung vorbereiten.', parts=True, tool_required=True, sampling_required=False, links=('error', 'sampling')),
    'sampling_preparation': dict(label='Musterungsvorbereitung', hint='Werkzeug, Unterlagen und Aufgaben für die anstehende Musterung vorbereiten.', parts=False, tool_required=True, sampling_required=False, links=('sampling',)),
    'sampling_work': dict(label='Musterung bearbeiten / begleiten', hint='Eine bestehende Musterung zuordnen und die begleitenden Arbeiten dokumentieren.', parts=False, tool_required=False, sampling_required=True, links=('sampling',)),
    'tool_transfer': dict(label='Werkzeugverlagerung', hint='Übernahme oder Verlagerung eines Werkzeugs und die nächsten Schritte dokumentieren.', parts=False, tool_required=True, sampling_required=False, links=('sampling',)),
    'tool_acceptance': dict(label='Werkzeugabnahme', hint='Prüfung, Abnahmebefunde und offene Punkte zum Werkzeug dokumentieren.', parts=False, tool_required=True, sampling_required=False, links=('sampling',)),
    'other': dict(label='Sonstiges', hint='Den konkreten Anlass und das Ziel in der Beschreibung festhalten.', parts=False, tool_required=False, sampling_required=False, links=('sampling', 'error')),
    'legacy': dict(label='Noch nicht eingeordnet', hint='Bestehendes Projekt: Projektgrund in der Projektverwaltung festlegen.', parts=True, tool_required=False, sampling_required=False, links=('sampling', 'error')),
}
LINK_LABELS = {'sampling': 'Musterung', 'error': 'Fehlermeldung'}


def profile(kind):
    return PROJECT_TYPES.get(kind, PROJECT_TYPES['legacy'])


def validate_kind(value, allow_legacy=False):
    if value not in PROJECT_TYPES or (value == 'legacy' and not allow_legacy):
        raise ValueError('Bitte einen gültigen Projektgrund auswählen.')
    return value


def validate_reference(kind, tool_no, has_sampling):
    config = profile(kind)
    if config['sampling_required'] and not has_sampling:
        raise ValueError('Für dieses Projekt bitte eine bestehende Musterung auswählen bzw. zuerst verknüpfen.')
    if config['tool_required'] and not tool_no:
        raise ValueError('Für diesen Projektgrund ist ein Werkzeug erforderlich. Eine Musterung mit zugeordnetem Werkzeug ist ebenfalls möglich.')
