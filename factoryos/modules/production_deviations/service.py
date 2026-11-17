from math import ceil
from hashlib import sha256
import json
from sqlalchemy import inspect
from factoryos.extensions import db
from .models import ProductionDeviationConfirmation as Confirmation

REASONS=('Zykluszeit bewusst erhöht','Zykluszeit bewusst reduziert','Prozess-/Qualitätsprobleme','Störung oder Unterbrechung nicht gebucht','Kavitäten / aktive Nester abweichend','Ausschuss / Nacharbeit','Mengenmeldung fehlt oder verspätet','Auftragsabschluss noch nicht gebucht','Start-/Endzeit fehlerhaft','Soll-Zykluszeit / Stammdaten prüfen','Sonstiger Grund')

def evaluate(order,stats):
    forecast=stats.get('forecast');actual=stats['working_seconds'];planned=stats['planned_seconds']
    result=dict(kind=None,title='Keine bewertbare Abweichung',css='',confirmation=None,history=[],signature='',snapshot={},explanation='')
    if not forecast or not planned or order.is_project:return result
    expected=planned;kind=None
    known=not forecast['cavities_assumed']
    if stats['active_booking'] and stats['target']>0 and stats['good']>=stats['target']:
        kind='closure_missing';title='Gut-Sollmenge gemeldet – Auftrag läuft noch';css='deviation-overdue'
        explanation='Sollmenge laut Gutmeldungen erreicht. Tatsächliche Produktion und fehlenden Auftragsabschluss prüfen; dies beweist keine langsamere Zykluszeit.'
    elif stats['active_booking'] and actual>planned+max(60,planned*0.05):
        kind='overdue';title='Soll-Laufzeit überschritten – Auftrag läuft weiter';css='deviation-overdue'
        explanation='Keine gemessene Zyklusabweichung: Ursache kann langsamerer Prozess, fehlende Mengen-/Störungsmeldung oder eine fehlerhafte Zeit-/Sollvorgabe sein.'
    elif stats['active_booking'] and actual>=planned:
        kind='nominal_reached';title='Rechnerisches Sollende erreicht – Mengen und Abschluss prüfen';css='deviation-faster'
        explanation='Sollzeit aufgebraucht, aber noch kein bestätigtes Ende. Innerhalb der 5-%-/60-Sekunden-Toleranz zunächst Prüfhinweis, keine festgestellte langsamere Zykluszeit.'
    elif stats['is_complete'] and not stats['active_booking'] and stats['good']+stats['scrap']>0 and known:
        expected=ceil((stats['good']+stats['scrap'])/forecast['parts_per_cycle'])*forecast['cycle_time_s']
        tolerance=max(60,expected*0.05)
        if actual>expected+tolerance:kind='slower';title='Gebuchte Produktion langsamer als Sollvergleich';css='deviation-overdue'
        elif actual<expected-tolerance and actual>0:kind='faster';title='Gebuchte Produktion schneller als Sollvergleich';css='deviation-faster'
        explanation='Vergleich aus bestätigter Gut-/Ausschussmenge und gebuchter Produktionszeit innerhalb des Arbeitskalenders; kein gemessener Maschinenzyklus.'
    if kind:
        if not known:explanation+=' Vorläufig: Kavitäten fehlen; ein Teil je Zyklus wird angenommen.'
        facts=dict(order_id=order.id,target=stats['target'],cycle=forecast['cycle_time_s'],cavities=forecast['parts_per_cycle'],assumed=not known,good=stats['good'],scrap=stats['scrap'],complete=stats['is_complete'],kind=kind,bookings=[(b.id,b.machine_id,b.type,str(b.start_time),str(b.end_time)) for b in stats['bookings']])
        facts['calendar']=stats.get('calendar_basis',[])
        signature=sha256(json.dumps(facts,sort_keys=True).encode()).hexdigest()
        result.update(kind=kind,title=title,css=css,signature=signature,explanation=explanation,snapshot=dict(facts=facts,expected_seconds=expected,recorded_seconds=actual,difference_seconds=actual-expected,percent=(actual/expected-1)*100 if expected else None,observed_at=stats['now'].isoformat()))
    if inspect(db.engine).has_table(Confirmation.__tablename__):
        result['history']=Confirmation.query.filter_by(order_id=order.id).order_by(Confirmation.id.desc()).limit(10).all()
        if kind:result['confirmation']=Confirmation.query.filter_by(order_id=order.id,signature=result['signature']).order_by(Confirmation.id.desc()).first()
    return result
