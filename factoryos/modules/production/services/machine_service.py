"""Compatibility adapters; no independent machine-state writer remains."""
from uuid import uuid4
from .machine_control_service import execute,snapshot,current_booking

def get_active_machine_state(machine_id):
    booking=current_booking(machine_id)
    return {"status":booking.process if booking else "FREI","booking":booking}

def _command(machine_id,user_id,action,**kwargs):
    return execute(machine_id,user_id,action,str(uuid4()),snapshot(machine_id)["revision"],**kwargs)[0]

def start_setup(machine_id,user_id,tool_no,order_id=None,mode="RUEST",comment=None):
    if mode not in ("RUEST","ABRUEST"): raise ValueError("Unbekannter Rüstmodus.")
    return _command(machine_id,user_id,"setup" if mode=="RUEST" else "unsetup",
                    order_id=order_id,tool_no=tool_no,comment=comment)

def start_machine_event(machine_id,user_id,event,comment=None):
    if event not in ("WARTUNG","SONSTIG"): raise ValueError("Unbekannter Maschinenvorgang.")
    return _command(machine_id,user_id,"maintenance" if event=="WARTUNG" else "other",comment=comment)

def start_machine_downtime(machine_id,user_id,reason_id=None,comment=None,prev_order_id=None,tool_no=None):
    # Context always comes from server state, never caller-supplied previous orders.
    return _command(machine_id,user_id,"fault",reason_id=reason_id,comment=comment)

def close_all_active_bookings(machine_id):
    raise ValueError("Stille Ablösung aktiver Maschinenbuchungen ist gesperrt. Zentrale Maschinenbedienung verwenden.")

def start_machine_free(machine_id,user_id):
    raise ValueError("Frei-Buchungen werden ausschließlich durch einen geprüften Maschinenbefehl angelegt.")
