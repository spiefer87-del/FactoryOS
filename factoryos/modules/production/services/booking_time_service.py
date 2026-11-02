"""Audited start correction: UTC storage, Berlin input, optimistic revision and no real overlaps."""
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
import re
from sqlalchemy import or_
from factoryos.extensions import db
from factoryos.core.services.change_log_service import log_change
from factoryos.modules.production.models import TimeBooking
from .order_statistics import LOCAL_ZONE, local_label

def parse_local_start(value, fold=""):
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?",value):
        raise ValueError("Bitte Datum UND Uhrzeit mit Stunden/Minuten angeben.")
    try: naive = datetime.fromisoformat(value)
    except (ValueError,TypeError): raise ValueError("Bitte Datum und Uhrzeit angeben.")
    if naive.tzinfo is not None: raise ValueError("Bitte lokale Uhrzeit ohne UTC-Offset eingeben.")
    candidates = {}
    for side in (0,1):
        aware = naive.replace(tzinfo=LOCAL_ZONE,fold=side)
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(LOCAL_ZONE).replace(tzinfo=None)==naive:
            candidates[side] = utc.replace(tzinfo=None)
    if not candidates: raise ValueError("Diese Uhrzeit existiert wegen der Zeitumstellung nicht.")
    if len(set(candidates.values()))>1:
        if fold not in ("0","1"): raise ValueError("Doppelte Uhrzeit bei Zeitumstellung: erste oder zweite Stunde auswählen.")
        return candidates[int(fold)]
    return next(iter(candidates.values()))

def eligible(booking):
    if not booking.order or not booking.machine_id or booking.process not in ("PROD","MUSTER") or booking.type!="START":
        raise ValueError("Nur Produktions-/Musterungs-Startbuchungen können hier korrigiert werden.")
    if booking.order.sampling and booking.order.sampling.state=="completed":
        raise ValueError("Abgeschlossene Musterungen bleiben schreibgeschützt.")

def related_bookings(booking):
    return TimeBooking.query.filter(or_(TimeBooking.machine_id==booking.machine_id,
                                       TimeBooking.order_id==booking.order_id)).order_by(TimeBooking.id).all()

def revision(booking):
    rows = related_bookings(booking)
    payload = [(row.id,row.order_id,row.machine_id,row.process,row.type,
                row.start_time.isoformat(),row.end_time.isoformat() if row.end_time else None) for row in rows]
    payload.append(("sampling",booking.order.sampling.state if booking.order.sampling else None))
    return sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

def correction_plan(booking, new_start, reason, now=None):
    eligible(booking)
    now = now or datetime.utcnow()
    if not 5<=len(reason.strip())<=1000: raise ValueError("Bitte eine Begründung mit 5 bis 1000 Zeichen angeben.")
    if new_start>now: raise ValueError("Eine tatsächliche Startzeit darf nicht in der Zukunft liegen.")
    if booking.end_time and new_start>=booking.end_time: raise ValueError("Start muss vor dem Ende der Buchung liegen.")
    if booking.start_time.replace(microsecond=0)==new_start.replace(microsecond=0):
        raise ValueError("Die Startzeit ist unverändert.")
    end = booking.end_time or datetime.max
    changes = []
    for other in related_bookings(booking):
        if other.id==booking.id or (other.end_time and other.end_time<=other.start_time):
            continue
        other_end = other.end_time or datetime.max
        if other.start_time>=end or other_end<=new_start: continue
        # Only automatically generated, already ended FREE intervals may be shortened.
        if (other.machine_id==booking.machine_id and other.process=="FREI" and other.order_id is None
                and other.end_time is not None and other.end_time<=booking.start_time+timedelta(seconds=1)
                and new_start<booking.start_time):
            corrected_end = max(other.start_time,new_start)
            changes.append({"id":other.id,"old_end":other.end_time,"new_end":corrected_end})
            continue
        if (other.machine_id==booking.machine_id or
                (other.order_id==booking.order_id and other.process in ("PROD","MUSTER"))):
            label = other.order.order_no if other.order else other.process
            raise ValueError(f"Überschneidung mit Buchung #{other.id} ({label}, {local_label(other.start_time)}). Bitte diese Buchung zuerst fachlich klären.")
    return changes

def apply_correction(booking, new_start, reason, expected_revision):
    old_start, old_end = booking.start_time, booking.end_time
    # Acquire the write lock before rechecking all dependent records.
    statement = TimeBooking.query.filter_by(id=booking.id,start_time=old_start,end_time=old_end)
    if statement.update({TimeBooking.start_time:old_start},synchronize_session=False)!=1:
        raise ValueError("Buchung wurde parallel geändert. Bitte neu laden.")
    db.session.expire_all()
    booking = db.session.get(TimeBooking,booking.id)
    eligible(booking)
    if revision(booking)!=expected_revision:
        raise ValueError("Buchungen wurden seit der Vorschau geändert. Bitte neu laden und erneut prüfen.")
    changes = correction_plan(booking,new_start,reason)
    adjustments = []
    for item in changes:
        free = db.session.get(TimeBooking,item["id"])
        free.end_time=item["new_end"]
        adjustments.append({"booking_id":free.id,"old_end_utc":item["old_end"].isoformat(),
                            "new_end_utc":item["new_end"].isoformat()})
    booking.start_time=new_start
    entry = {"booking_id":booking.id,"machine_id":booking.machine_id,"reason":reason.strip(),
             "start_time_utc":{"old":old_start.isoformat(),"new":new_start.isoformat()},
             "free_intervals":adjustments}
    log_change("order",booking.order_id,"update",entity_name=booking.order.order_no,
               category="production",changes={"booking_start_correction":entry})
    if booking.order.sampling:
        log_change("sampling",booking.order.sampling.id,"update",entity_name=booking.order.order_no,
                   category="production",changes={"booking_start_correction":entry})
    db.session.commit()
    return booking
