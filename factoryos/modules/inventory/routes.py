from uuid import uuid4
from flask import Blueprint,render_template,request,redirect,url_for,flash,abort
from flask_login import current_user,login_required
from factoryos.extensions import db
from factoryos.core.auth import permission_required
from factoryos.core.access_control import valid_csrf
from factoryos.modules.orders.models import Order
from factoryos.modules.masterdata.articles.models import Article
from .models import WarehouseLocation as Location,WarehouseLot as Lot,WarehouseReservation as Reservation,WarehouseEvent as Event
from .service import LABELS,PERMISSIONS,execute,revision,confirmed,allocated,pending,stock_rows,Conflict

bp=Blueprint('inventory',__name__,url_prefix='/warehouse')

@bp.get('/journal/<int:event_id>')
@login_required
@permission_required('inventory.view')
def event_detail(event_id):
    event=Event.query.get_or_404(event_id)
    from factoryos.models.user import User
    return render_template('inventory/event.html',event=event,labels=LABELS,user=db.session.get(User,event.user_id),
        lot=db.session.get(Lot,event.lot_id) if event.lot_id else None,places={p.id:p.code for p in Location.query.all()})
FIELDS={
 'cancel':['lot_id','quantity'],
 'location':['code','description'], 'transfer':['order_id','article_id','batch','quantity'],
 'opening':['article_id','batch','quantity','destination_id'], 'receive':['lot_id','quantity','destination_id'],'reject':['lot_id','quantity'],
 'move':['lot_id','location_id','status','quantity','destination_id'],'block':['lot_id','location_id','quantity'],'release':['lot_id','location_id','quantity'],
 'scrap':['lot_id','location_id','status','quantity'],'reserve':['lot_id','location_id','quantity','reference'],
 'pick':['reservation_id'],'ship':['reservation_id','quantity'],'unreserve':['reservation_id','quantity'],'return':['event_id','quantity','destination_id'],'reverse':['event_id','quantity']}
NAMES={'code':'Lagerplatz-Code','description':'Lagerplatzbeschreibung','order_id':'Fertigungsauftrag','article_id':'Artikel aus Stammdaten',
 'batch':'Los / Charge / Behälterkennung','quantity':'Menge (ganze Stück)','destination_id':'Ziellagerplatz','lot_id':'Produktionslos / Übergabe',
 'location_id':'Quelllagerplatz','status':'Bestandsstatus','reference':'Empfänger / Versandbeleg','reservation_id':'Reservierung','event_id':'Bezugsbuchung'}

@bp.get('/')
@login_required
@permission_required('inventory.view')
def dashboard():
    view=request.args.get('view','overview')
    if view not in ('overview','incoming','stock','outbound','locations','journal'):abort(404)
    lots=Lot.query.order_by(Lot.id.desc()).all()
    candidates=[]
    if view in ('overview','incoming'):
        for order in Order.query.filter_by(is_project=False).order_by(Order.id.desc()):
            if order.sampling:continue
            good,scrap=confirmed(order);remaining=good-allocated(order.id)
            if remaining>0:candidates.append(dict(order=order,good=good,scrap=scrap,remaining=remaining))
    return render_template('inventory/dashboard.html',view=view,labels=LABELS,lots=lots,pending=pending,
        candidates=candidates,stocks=stock_rows(),locations=Location.query.order_by(Location.code).all(),
        reservations=Reservation.query.order_by(Reservation.id.desc()).all(),events=Event.query.order_by(Event.id.desc()).all())

def render_action(action,data=None,error=None,status=200):
    data=data or {}
    choices={
      'order_id':[(o.id,o.order_no+' · '+(o.article or 'Ohne Artikel')) for o in Order.query.filter_by(is_project=False).order_by(Order.order_no) if not o.sampling],
      'article_id':[(a.id,a.article_no+' · '+(a.article_name or '')) for a in Article.query.order_by(Article.article_no)],
      'lot_id':[(l.id,f'Los #{l.id} · {l.article_no} · {l.batch} · Auftrag {l.order_no or "Erstbestand"} · Übergabe offen {pending(l)}') for l in Lot.query.order_by(Lot.id.desc())],
      'location_id':[(p.id,p.code+' · '+p.description) for p in Location.query.order_by(Location.code)],
      'status':[('free','Verfügbar (unreserviert)'),('blocked','Gesperrt')],
      'reservation_id':[(r.id,f'#{r.id} · Los {r.lot_id} · {r.reference} · offen {r.remaining} · {r.state}') for r in Reservation.query.filter(Reservation.remaining>0).order_by(Reservation.id.desc())],
      'event_id':[(e.id,f'#{e.id} · {LABELS.get(e.kind,e.kind)} · Los {e.lot_id} · {e.quantity} Stück') for e in Event.query.filter(Event.kind.in_(('ship',) if action=='return' else ('opening','receive','reject','move','block','release','scrap'))).order_by(Event.id.desc())]}
    choices['destination_id']=choices['location_id']
    return render_template('inventory/action.html',action=action,label=LABELS[action],fields=FIELDS[action],names=NAMES,choices=choices,data=data,error=error,
        revision=revision(),command_id=str(uuid4())),status

def action_view(action):
    @login_required
    @permission_required(PERMISSIONS[action])
    def handler():
        if request.method=='GET':return render_action(action,request.args.to_dict())
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        data={key:request.form.get(key,'') for key in FIELDS[action]+['confirmed','reason']}
        try:
            event,replayed=execute(current_user.id,action,request.form.get('command_id'),request.form.get('revision'),data)
            flash(('Bereits verbucht: ' if replayed else 'Gebucht: ')+LABELS[action]+f' · Journal #{event.id}','success')
            return redirect(url_for('inventory.dashboard',view='journal'),code=303)
        except PermissionError:db.session.rollback();abort(403)
        except ValueError as error:
            db.session.rollback();return render_action(action,data,str(error),409 if isinstance(error,Conflict) else 422)
    return handler

for action in LABELS:
    bp.add_url_rule('/'+action,endpoint=action,view_func=action_view(action),methods=['GET','POST'])
