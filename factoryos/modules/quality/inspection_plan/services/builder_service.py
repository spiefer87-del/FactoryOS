"""Validated module editing; caller owns transaction and revision lock."""
import hashlib
import json
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask_login import current_user
from factoryos.extensions import db
from ..definitions import STATUS_LABELS
from ..models import QualityInspectionCheck
from .change_log_service import log_change


class PlanValidation(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('; '.join(errors.values()))


def revision_token(version):
    def row(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    data = {'version': row(version), 'sections': [], 'siblings': [(v.id, v.status) for v in version.plan.versions]}
    for section in version.sections:
        data['sections'].append([row(section), *[[row(x) for x in getattr(section, key)] for key in ('checks','characteristics','gauge_checks','images','snippets')]])
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def changed(version, action, message):
    version.is_dirty = True
    log_change(version, action, f'Revision {version.revision}: {message}', current_user.id)


def text(data, key, label, maxlen, errors, required=False):
    value = str(data.get(key) or '').strip()
    if required and not value: errors[key] = f'{label}: Bitte ausfüllen.'
    elif len(value) > maxlen: errors[key] = f'{label}: Höchstens {maxlen} Zeichen.'
    return value


def numeric(value, key, label, errors, *, positive=False):
    if not value: return
    try:
        number = Decimal(value.replace(',', '.'))
        if not number.is_finite() or number < 0 or (positive and number <= 0): raise InvalidOperation
    except InvalidOperation:
        errors[key] = f'{label}: Bitte eine {"positive" if positive else "nicht negative"} Zahl ohne Einheit eingeben (Dezimalkomma erlaubt).'


def save_settings(section, data):
    errors = {}
    values = {key: text(data, key, label, limit, errors, required) for key,label,limit,required in (
        ('title','Modulbezeichnung',200,True), ('frequency','Prüfintervall / Anlass',200,True),
        ('sample_size','Stichprobenumfang',100,True), ('responsible','Verantwortung',100,True),
        ('instructions','Prüfanweisung',4000,False))}
    if errors: raise PlanValidation(errors)
    section.title = values.pop('title')
    section.inspection_settings = values
    changed(section.version, 'UPDATE_MODULE', f'Modul {section.title}: Prüfumfang und Anweisung geändert')


def save_check(section, data, check=None):
    errors = {}
    values = {key: text(data,key,label,limit,errors,required) for key,label,limit,required in (
        ('name','Prüfmerkmal',200,True), ('requirement','Annahme- / Fehlerkriterium',4000,True),
        ('method','Prüfmethode / Hilfsmittel',300,True), ('target_value','Sollwert',50,section.section_type=='weight'),
        ('tolerance_minus','Toleranz minus',50,section.section_type=='weight'),
        ('tolerance_plus','Toleranz plus',50,section.section_type=='weight'), ('unit','Einheit',20,section.section_type=='weight'))}
    if section.section_type=='weight':
        for key in ('target_value','tolerance_minus','tolerance_plus'):
            numeric(values[key], key, {'target_value':'Sollgewicht','tolerance_minus':'Toleranz minus','tolerance_plus':'Toleranz plus'}[key], errors, positive=key=='target_value')
        if values['unit'] not in ('g','kg','mg'): errors['unit']='Einheit: Bitte g, kg oder mg angeben.'
        try:
            if Decimal(values['tolerance_minus'].replace(',','.')) > Decimal(values['target_value'].replace(',','.')):
                errors['tolerance_minus']='Toleranz minus: Untere Gewichtsgrenze darf nicht negativ sein.'
        except InvalidOperation: pass
    if errors: raise PlanValidation(errors)
    if check is None:
        check=QualityInspectionCheck(section=section,sort_order=max([x.sort_order or 0 for x in section.checks]+[0])+1)
        db.session.add(check)
    for key,value in values.items(): setattr(check,key,value)
    changed(section.version,'SAVE_CHECK',f'{section.title}: Merkmal {check.name} gespeichert')
    return check


def readiness_errors(version):
    errors = {}
    if not version.sections: errors['modules']='Bitte mindestens ein ausgefülltes Prüfmodul hinzufügen.'
    for section in version.sections:
        prefix=f'Modul {section.title}'
        settings=section.inspection_settings or {}
        for key,label in (('frequency','Prüfintervall'),('sample_size','Stichprobenumfang'),('responsible','Verantwortung')):
            if not settings.get(key): errors[f'section-{section.id}-{key}']=f'{prefix}: {label} fehlt.'
        if section.section_type=='dimension':
            if not section.characteristics: errors[f'section-{section.id}']=f'{prefix}: Prüfmaße fehlen.'
            for char in section.characteristics:
                if not all(str(getattr(char,k) or '').strip() for k in ('name','target_value','tolerance_minus','tolerance_plus','unit')):
                    errors[f'characteristic-{char.id}']=f'{prefix}: Prüfmaß {char.sort_order} ist unvollständig.'
                invalid={}
                for key in ('tolerance_minus','tolerance_plus'):numeric(getattr(char,key) or '',key,key,invalid)
                if invalid:errors[f'characteristic-{char.id}']=f'{prefix}: Prüfmaß {char.sort_order} hat ungültige Toleranzen.'
        elif section.section_type=='gauge':
            if not section.gauge_checks: errors[f'section-{section.id}']=f'{prefix}: Lehrenmerkmale fehlen.'
            for check in section.gauge_checks:
                if not check.name or not check.method or not check.gauge or check.gauge.status!='active':
                    errors[f'gauge-{check.id}']=f'{prefix}: Merkmal, Methode oder aktives Prüfmittel fehlt.'
                elif check.gauge.next_calibration and check.gauge.next_calibration < date.today():
                    errors[f'gauge-{check.id}']=f'{prefix}: Prüfmittel {check.gauge.gauge_no} ist zur Kalibrierung fällig.'
        else:
            if not section.checks: errors[f'section-{section.id}']=f'{prefix}: Prüfmerkmale mit Annahmekriterien fehlen.'
            for check in section.checks:
                try: save_check_values_valid(section,check)
                except PlanValidation as error:
                    errors[f'check-{check.id}']=f'{prefix}, {check.name}: '+str(error)
    return errors


def save_check_values_valid(section, check):
    # Validate without assigning, logging or dirtying the session.
    errors={}
    for key in ('name','requirement','method'):
        if not getattr(check,key): errors[key]='Pflichtangabe fehlt'
    if section.section_type=='weight':
        for key in ('target_value','tolerance_minus','tolerance_plus'):
            value=getattr(check,key)
            if not value: errors[key]='Gewichtsangabe fehlt'
            else: numeric(value,key,key,errors,positive=key=='target_value')
        if check.unit not in ('g','kg','mg'): errors['unit']='Gewichtseinheit fehlt'
    if errors: raise PlanValidation(errors)


def workflow(version, action):
    latest=max(version.plan.versions,key=lambda v:v.id)
    if latest.id!=version.id: raise PlanValidation({'workflow':'Historische Revision: Bitte die neueste Revision öffnen.'})
    transitions={('draft','review'):'review',('review','return'):'draft',('review','release'):'released',('released','close'):'closed'}
    target=transitions.get((version.status,action))
    if not target: raise PlanValidation({'workflow':'Diese Statusänderung ist im aktuellen Zustand nicht möglich.'})
    if target in ('review','released'):
        errors=readiness_errors(version)
        if errors: raise PlanValidation(errors)
    if target=='released':
        version.released_at=datetime.utcnow();version.released_by_id=current_user.id;version.is_dirty=False
    previous=version.status;version.status=target
    log_change(version,'STATUS',f'Revision {version.revision}: {STATUS_LABELS[previous]} → {STATUS_LABELS[target]}',current_user.id)
