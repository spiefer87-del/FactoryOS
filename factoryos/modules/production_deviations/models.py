from datetime import datetime
from factoryos.extensions import db

class ProductionDeviationConfirmation(db.Model):
    __tablename__='production_deviation_confirmations'
    id=db.Column(db.Integer,primary_key=True)
    order_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    signature=db.Column(db.String(64),nullable=False,index=True)
    kind=db.Column(db.String(40),nullable=False)
    category=db.Column(db.String(100),nullable=False)
    reason=db.Column(db.Text,nullable=False)
    snapshot=db.Column(db.JSON,nullable=False)
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    author=db.relationship('User')
