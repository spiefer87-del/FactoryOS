from uuid import uuid4
from sqlalchemy import func
from factoryos.extensions import db
from factoryos.models.machine import Machine
from factoryos.modules.production.models import TimeBooking
from factoryos.modules.orders.models import Order
from .machine_control_service import execute,snapshot,current_booking,TERMINAL

FINISHED_ORDER_STATUSES=tuple(TERMINAL)

def get_manual_start_data():
    machines=Machine.query.filter_by(machine_status="aktiv").order_by(Machine.machine_no,Machine.name).all()
    orders=Order.query.filter(~func.lower(func.coalesce(Order.status,"")).in_(FINISHED_ORDER_STATUSES)).order_by(Order.order_no).all()
    active=TimeBooking.query.filter_by(end_time=None).order_by(TimeBooking.start_time.desc()).all()
    by_machine={};by_order={}
    for b in active:
        if b.machine_id:by_machine.setdefault(b.machine_id,b)
        if b.order_id:by_order.setdefault(b.order_id,b)
    return dict(machines=machines,orders=orders,active_by_machine=by_machine,active_by_order=by_order)

def start_production(user_id,order_id,machine_id,comment=None):
    execute(int(machine_id),user_id,"start",str(uuid4()),snapshot(int(machine_id))["revision"],
            order_id=order_id,comment=comment)
    return current_booking(int(machine_id))

def end_booking(booking_id,user_id,action):
    booking=db.session.get(TimeBooking,booking_id)
    if not booking or not booking.machine_id or booking.end_time is not None:
        raise ValueError("Maschinenbuchung ist nicht mehr aktiv.")
    if action not in ("PAUSE","STOP"):raise ValueError("Unbekannter Stoppbefehl.")
    return execute(booking.machine_id,user_id,"pause" if action=="PAUSE" else "stop",str(uuid4()),
        snapshot(booking.machine_id)["revision"],comment="Vorgang manuell beendet" if action=="STOP" else "")

def resume_booking(booking_id,user_id):
    booking=db.session.get(TimeBooking,booking_id)
    if not booking or not booking.machine_id or booking.end_time is not None or booking.process!="PAUSE":
        raise ValueError("Nur eine aktive Pause kann fortgesetzt werden. Störung zuerst ausdrücklich entstören.")
    return execute(booking.machine_id,user_id,"resume",str(uuid4()),snapshot(booking.machine_id)["revision"])
