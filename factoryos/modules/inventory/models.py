from datetime import datetime
from sqlalchemy import event
from factoryos.extensions import db

class WarehouseLocation(db.Model):
    __tablename__='warehouse_locations'
    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(80),unique=True,nullable=False)
    description=db.Column(db.String(200),nullable=False)

class WarehouseLot(db.Model):
    __tablename__='warehouse_lots'
    id=db.Column(db.Integer,primary_key=True)
    order_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=True,index=True)
    article_id=db.Column(db.Integer,db.ForeignKey('articles.id'),nullable=False)
    article_no=db.Column(db.String(120),nullable=False)
    article_name=db.Column(db.String(255),nullable=False)
    order_no=db.Column(db.String(50))
    tool_no=db.Column(db.String(50))
    batch=db.Column(db.String(100),nullable=False)
    quantity=db.Column(db.Integer,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    origin=db.Column(db.String(20),nullable=False) # production / opening

class WarehouseReservation(db.Model):
    __tablename__='warehouse_reservations'
    id=db.Column(db.Integer,primary_key=True)
    lot_id=db.Column(db.Integer,db.ForeignKey('warehouse_lots.id'),nullable=False)
    location_id=db.Column(db.Integer,db.ForeignKey('warehouse_locations.id'),nullable=False)
    quantity=db.Column(db.Integer,nullable=False)
    remaining=db.Column(db.Integer,nullable=False)
    state=db.Column(db.String(20),nullable=False) # reserved / picked / closed
    reference=db.Column(db.String(200),nullable=False)

class WarehouseEvent(db.Model):
    __tablename__='warehouse_events'
    id=db.Column(db.Integer,primary_key=True)
    command_id=db.Column(db.String(36),unique=True,nullable=False)
    payload_hash=db.Column(db.String(64),nullable=False)
    kind=db.Column(db.String(30),nullable=False)
    lot_id=db.Column(db.Integer,db.ForeignKey('warehouse_lots.id'))
    reservation_id=db.Column(db.Integer,db.ForeignKey('warehouse_reservations.id'))
    quantity=db.Column(db.Integer,nullable=False)
    transfer_effect=db.Column(db.Integer,nullable=False,default=0)
    related_id=db.Column(db.Integer,db.ForeignKey('warehouse_events.id'))
    reversal_of=db.Column(db.Integer,db.ForeignKey('warehouse_events.id'),unique=True)
    reason=db.Column(db.String(500),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow,nullable=False)
    details=db.Column(db.JSON,nullable=False)
    lines=db.relationship('WarehouseLine',backref='event',order_by='WarehouseLine.id')

class WarehouseLine(db.Model):
    __tablename__='warehouse_lines'
    id=db.Column(db.Integer,primary_key=True)
    event_id=db.Column(db.Integer,db.ForeignKey('warehouse_events.id'),nullable=False,index=True)
    lot_id=db.Column(db.Integer,db.ForeignKey('warehouse_lots.id'),nullable=False,index=True)
    location_id=db.Column(db.Integer,db.ForeignKey('warehouse_locations.id'),nullable=False)
    status=db.Column(db.String(10),nullable=False) # free / blocked
    quantity=db.Column(db.Integer,nullable=False)

class WarehouseLock(db.Model):
    __tablename__='warehouse_lock'
    id=db.Column(db.Integer,primary_key=True)
    version=db.Column(db.Integer,nullable=False,default=0)

def immutable(*args):raise ValueError('Lagerjournal ist unveränderlich. Bitte eine Gegenbuchung verwenden.')
for model in (WarehouseEvent,WarehouseLine,WarehouseLot):
    event.listen(model,'before_update',immutable)
    event.listen(model,'before_delete',immutable)
