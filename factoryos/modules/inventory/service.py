"""Atomic stock ledger. All quantities are confirmed whole pieces, never estimates."""
import hashlib,json,re
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert
from factoryos.extensions import db
from factoryos.core.auth import has_permission
from factoryos.models.user import User
from factoryos.modules.orders.models import Order
from factoryos.modules.production.models import OrderCompletion,QuantityReport
from factoryos.modules.masterdata.articles.models import Article
from .models import WarehouseLocation as Location,WarehouseLot as Lot,WarehouseEvent as Event,WarehouseLine as Line,WarehouseReservation as Reservation,WarehouseLock as Lock

LABELS={'location':'Lagerplatz anlegen','transfer':'Produktionsübergabe','cancel':'Unübernommene Übergabe stornieren','receive':'Lagerannahme','reject':'Ausschuss vor Lagerannahme','opening':'Erstbestand',
    'move':'Umlagern','block':'Bestand sperren','release':'Bestand freigeben','scrap':'Lagerausschuss','reserve':'Reservieren',
    'pick':'Kommissionieren','unreserve':'Reservierung freigeben','ship':'Versand bestätigen','return':'Rücknahme in Sperrbestand','reverse':'Gegenbuchung'}
PERMISSIONS={k:'inventory.'+('locations' if k=='location' else 'production' if k=='transfer' else 'receive' if k in ('receive','reject') else 'release' if k in ('release','block') else 'adjust' if k in ('opening','reverse','cancel') else 'dispatch' if k in ('reserve','pick','unreserve','ship','return') else 'move' if k=='move' else 'scrap') for k in LABELS}

class Conflict(ValueError):pass

def quantity(raw,label='Menge'):
    if isinstance(raw,bool) or not re.fullmatch(r'[0-9]{1,10}',str(raw or '')):raise ValueError(label+': positive ganze Stückzahl ohne Einheit eingeben.')
    value=int(raw)
    if not 0<value<=2147483647:raise ValueError(label+': zulässig sind 1 bis 2147483647 Stück.')
    return value

def text(data,key,label,limit,required=True):
    value=str(data.get(key) or '').strip()
    if (required and not value) or len(value)>limit:raise ValueError(f'{label}: bitte ausfüllen, höchstens {limit} Zeichen.')
    return value

def revision():
    row=db.session.get(Lock,1)
    return str(row.version if row else 0)

def confirmed(order):
    completion=OrderCompletion.query.filter_by(order_id=order.id).first()
    if completion:return completion.good_qty,completion.scrap_qty
    good,scrap=db.session.query(func.coalesce(func.sum(QuantityReport.good_qty),0),func.coalesce(func.sum(QuantityReport.scrap_qty),0)).filter_by(order_id=order.id).one()
    return int(good),int(scrap)

def allocated(order_id):return int(db.session.query(func.coalesce(func.sum(Lot.quantity),0)).filter(Lot.order_id==order_id,Lot.origin=='production',Lot.id.notin_(db.session.query(Event.lot_id).filter(Event.kind=='cancel',Event.lot_id.isnot(None)))).scalar())

def protect_final_total(order_id,good):
    from sqlalchemy import inspect
    if inspect(db.engine).has_table('warehouse_lots') and good<allocated(order_id):
        raise ValueError('Endgutmenge liegt unter bereits bestätigten Lagerübergaben. Bitte die Mengen vor dem Auftragsabschluss fachlich klären.')
def pending(lot):return lot.quantity-int(db.session.query(func.coalesce(func.sum(Event.transfer_effect),0)).filter_by(lot_id=lot.id).scalar()) if lot.origin=='production' else 0
def balance(lot,location,status):return int(db.session.query(func.coalesce(func.sum(Line.quantity),0)).filter_by(lot_id=lot,location_id=location,status=status).scalar())
def reserved(lot,location):return int(db.session.query(func.coalesce(func.sum(Reservation.remaining),0)).filter(Reservation.lot_id==lot,Reservation.location_id==location,Reservation.state.in_(('reserved','picked'))).scalar())
def available(lot,location):return balance(lot,location,'free')-reserved(lot,location)

def stock_rows():
    rows=db.session.query(Line.lot_id,Line.location_id,Line.status,func.sum(Line.quantity)).group_by(Line.lot_id,Line.location_id,Line.status).all()
    return [dict(lot=db.session.get(Lot,l),location=db.session.get(Location,p),status=s,quantity=int(n),reserved=reserved(l,p) if s=='free' else 0,available=available(l,p) if s=='free' else 0) for l,p,s,n in rows if n]

def execute(user_id,action,command_id,expected,data):
    with db.session.no_autoflush:
        return _execute(user_id,action,command_id,expected,data)

def _execute(user_id,action,command_id,expected,data):
    """Caller must rollback on every error; this function commits success only."""
    if action not in PERMISSIONS:raise ValueError('Unbekannte Lageraktion.')
    try:
        if str(UUID(command_id))!=command_id:raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ValueError('Buchungskennung fehlt. Bitte neu laden.')
    digest=hashlib.sha256(json.dumps(dict(action=action,data=data,revision=expected),sort_keys=True).encode()).hexdigest()
    # Same global production lock as completion: source and warehouse writes
    # cannot race a final quantity confirmation. Warehouse writers share it.
    from factoryos.modules.production.services.machine_control_service import acquire_control_lock
    acquire_control_lock()
    user=db.session.get(User,user_id)
    if not has_permission(user,PERMISSIONS[action]):raise PermissionError('Keine Berechtigung für diese Lagerbuchung.')
    previous=Event.query.filter_by(command_id=command_id).first()
    if previous:
        if previous.user_id!=user_id or previous.payload_hash!=digest:raise Conflict('Buchungskennung bereits anders verwendet.')
        db.session.commit();return previous,True
    db.session.execute(insert(Lock).values(id=1,version=0).on_conflict_do_nothing(index_elements=['id']))
    lock=db.session.get(Lock,1,populate_existing=True)
    if str(lock.version)!=str(expected):raise Conflict('Lagerstand wurde geändert. Bitte neu laden und Buchung erneut prüfen.')
    if data.get('confirmed')!='yes':raise ValueError('Buchung bitte ausdrücklich bestätigen.')
    reason=text(data,'reason','Begründung / Beleg',500)
    n=quantity(data.get('quantity')) if action not in ('location','pick') else 0
    event=Event(command_id=command_id,payload_hash=digest,kind=action,quantity=n,reason=reason,user_id=user_id,details=dict(data),transfer_effect=0)
    db.session.add(event)
    def get(model,key):
        raw=data.get(key)
        if not str(raw or '').isdigit():raise ValueError(key+': gültigen Datensatz auswählen.')
        row=db.session.get(model,int(raw))
        if not row:raise ValueError(key+': Datensatz nicht vorhanden.')
        return row
    def line(lot,place,status,amount):
        if status not in ('free','blocked'):raise ValueError('Bestandsstatus muss verfügbar oder gesperrt sein.')
        db.session.add(Line(event=event,lot_id=lot,location_id=place,status=status,quantity=amount))
    if action=='location':
        code=text(data,'code','Lagerplatz-Code',80).upper()
        if Location.query.filter_by(code=code).first():raise ValueError('Lagerplatz-Code ist bereits vorhanden.')
        place=Location(code=code,description=text(data,'description','Lagerplatzbeschreibung',200));db.session.add(place)
    elif action in ('transfer','opening'):
        article=get(Article,'article_id');order=get(Order,'order_id') if action=='transfer' else None
        if order:
            if order.is_project or order.sampling:raise ValueError('Projekt-/Musterungsauftrag ist keine reguläre Fertigwarenquelle.')
            if article.article_no!=order.article:raise ValueError('Artikelnummer stimmt nicht mit dem Auftrag überein. Bitte zuerst die Stammdaten/Auftragszuordnung korrigieren.')
            if n>confirmed(order)[0]-allocated(order.id):raise ValueError('Übergabemenge übersteigt die noch nicht übergebene bestätigte Gutmenge.')
            if Lot.query.filter(Lot.order_id==order.id,Lot.article_id!=article.id).first():raise Conflict('Auftrag wurde bereits einem anderen Artikel zugeordnet.')
            completion=OrderCompletion.query.filter_by(order_id=order.id).first()
            event.details={**event.details,'production_evidence':dict(good=confirmed(order)[0],scrap=confirmed(order)[1],completion_id=completion.id if completion else None,quantity_report_ids=[r.id for r in QuantityReport.query.filter_by(order_id=order.id).order_by(QuantityReport.id)])}
        lot=Lot(order_id=order.id if order else None,article_id=article.id,article_no=article.article_no,article_name=article.article_name or '',order_no=order.order_no if order else None,tool_no=order.tool_no if order else None,batch=text(data,'batch','Los / Charge',100),quantity=n,origin='production' if order else 'opening')
        db.session.add(lot);db.session.flush([lot]);event.lot_id=lot.id
        if action=='opening':line(lot.id,get(Location,'destination_id').id,'blocked',n)
    elif action=='cancel':
        lot=get(Lot,'lot_id');event.lot_id=lot.id
        if lot.origin!='production' or n!=lot.quantity or pending(lot)!=lot.quantity:raise Conflict('Nur eine vollständig offene, noch nicht übernommene Übergabe kann vollständig storniert werden.')
        event.transfer_effect=n
    elif action in ('receive','reject'):
        lot=get(Lot,'lot_id');event.lot_id=lot.id
        if lot.origin!='production' or n>pending(lot):raise ValueError('Menge übersteigt die offene Produktionsübergabe.')
        order=db.session.get(Order,lot.order_id)
        if not order or allocated(order.id)>confirmed(order)[0]:raise Conflict('Bestätigte Produktionsmenge und Übergaben sind widersprüchlich; zuerst fachlich klären.')
        event.transfer_effect=n
        if action=='receive':line(lot.id,get(Location,'destination_id').id,'blocked',n)
    elif action in ('reserve','move','block','release','scrap'):
        lot=get(Lot,'lot_id');place=get(Location,'location_id');event.lot_id=lot.id
        status=data.get('status','free')
        if action=='reserve':
            if n>available(lot.id,place.id):raise ValueError('Nicht genügend verfügbarer, unreservierter Bestand.')
            row=Reservation(lot_id=lot.id,location_id=place.id,quantity=n,remaining=n,state='reserved',reference=text(data,'reference','Empfänger / Versandbeleg',200));db.session.add(row);db.session.flush([row]);event.reservation_id=row.id
        else:
            if action=='block':status='free'
            if action=='release':status='blocked'
            if action=='move':
                destination=get(Location,'destination_id')
                if destination.id==place.id:raise ValueError('Quell- und Ziellagerplatz sind identisch.')
                line(lot.id,destination.id,status,n)
            elif action in ('block','release'):line(lot.id,place.id,'blocked' if action=='block' else 'free',n)
            line(lot.id,place.id,status,-n)
    elif action in ('pick','unreserve','ship'):
        row=get(Reservation,'reservation_id');event.lot_id=row.lot_id;event.reservation_id=row.id
        event.details={**event.details,'reservation_before':dict(remaining=row.remaining,state=row.state,reference=row.reference)}
        if row.state not in ('reserved','picked') or row.remaining<=0:raise Conflict('Reservierung ist bereits abgeschlossen.')
        if action=='pick':
            if row.state!='reserved':raise Conflict('Reservierung ist bereits kommissioniert.')
            row.state='picked';event.quantity=row.remaining
        else:
            if n>row.remaining:raise ValueError('Menge übersteigt die offene Reservierung.')
            if action=='ship':
                if row.state!='picked':raise ValueError('Vor Versand zuerst kommissionieren und bestätigen.')
                line(row.lot_id,row.location_id,'free',-n)
            row.remaining-=n
            if row.remaining==0:row.state='closed'
    elif action=='return':
        source=get(Event,'event_id')
        if source.kind!='ship':raise ValueError('Rücknahme benötigt eine bestätigte Versandbuchung.')
        returned=int(db.session.query(func.coalesce(func.sum(Event.quantity),0)).filter_by(kind='return',related_id=source.id).scalar())
        if n>source.quantity-returned:raise ValueError('Rücknahmemenge übersteigt die noch nicht zurückgenommene Versandmenge.')
        event.related_id=source.id;event.lot_id=source.lot_id
        line(source.lot_id,get(Location,'destination_id').id,'blocked',n)
    elif action=='reverse':
        source=get(Event,'event_id')
        if source.kind not in ('opening','receive','reject','move','block','release','scrap'):raise ValueError('Diese Buchung ist nicht direkt stornierbar. Reservierungen freigeben, Versand über Rücknahme korrigieren.')
        if Event.query.filter_by(reversal_of=source.id).first():raise Conflict('Buchung wurde bereits gegengebucht.')
        if n!=source.quantity:raise ValueError('Gegenbuchung muss die vollständige ursprüngliche Menge enthalten.')
        event.reversal_of=source.id;event.lot_id=source.lot_id;event.transfer_effect=-source.transfer_effect
        for old in source.lines:line(old.lot_id,old.location_id,old.status,-old.quantity)
    db.session.flush()
    # Validate final projection, including active reservations, for every touched bucket.
    touched={(l.lot_id,l.location_id,l.status) for l in event.lines}
    for lot,place,status in touched:
        if balance(lot,place,status)<0 or (status=='free' and available(lot,place)<0):raise Conflict('Buchung würde negativen oder bereits reservierten Bestand verbrauchen.')
    if event.lot_id:
        lot=db.session.get(Lot,event.lot_id)
        if lot.origin=='production' and not 0<=pending(lot)<=lot.quantity:raise Conflict('Übergabemenge ist widersprüchlich.')
    lock.version+=1;db.session.commit();return event,False
