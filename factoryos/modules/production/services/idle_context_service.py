"""Historical idle evidence and read-only machine-time evaluation."""
from datetime import datetime
from collections import defaultdict
from factoryos.extensions import db
from ..models import BookingIdleContext, MachineControlCommand, TimeBooking

WAIT_REASONS = {'material':'Material fehlt', 'temperature':'Aufheizen / Temperatur fehlt',
    'quality':'QS-Freigabe fehlt', 'staff':'Personal fehlt',
    'scheduled':'Geplanter späterer Produktionsstart', 'other':'Sonstiger Wartegrund'}

def validate_reason(code, note):
    if code not in WAIT_REASONS:raise ValueError('Bitte einen Wartegrund auswählen.')
    if len(note)>255:raise ValueError('Erläuterung: höchstens 255 Zeichen.')
    if code=='other' and len(note)<5:raise ValueError('Sonstigen Wartegrund mit mindestens 5 Zeichen erläutern.')

def record_idle(booking, mount, *, reason=None, note=None, source='transition'):
    if booking.process!='FREI':return
    if not booking.id:db.session.flush()
    status='unknown' if mount.get('requires_confirmation') or mount.get('operation') else mount.get('status','unknown')
    booking.idle_context=BookingIdleContext(tool_status=status,
        tool_no=mount.get('tool_no'),reason_code=reason,reason_note=note or None,source=source)

def idle_views(bookings, now=None):
    """One batch query for new evidence and one for matching legacy receipts."""
    now=now or datetime.utcnow()
    rows=[b for b in bookings if b.process=='FREI']
    ids=[b.id for b in rows]
    contexts={}
    for offset in range(0,len(ids),400):
        contexts.update({c.booking_id:c for c in BookingIdleContext.query.filter(BookingIdleContext.booking_id.in_(ids[offset:offset+400])).all()})
    legacy=[b.id for b in rows if b.id not in contexts]
    evidence=defaultdict(list)
    # IDs survive audited time corrections; timestamps alone are not reliable keys.
    for offset in range(0,len(legacy),400):
        for receipt in MachineControlCommand.query.filter(
                MachineControlCommand.after_state['active'][0]['id'].as_integer().in_(legacy[offset:offset+400])).all():
            active=(receipt.after_state or {}).get('active',[])
            if len(active)==1 and active[0].get('process')=='FREI':
                evidence[active[0]['id']].append((receipt.machine_id,(receipt.after_state or {}).get('tool_mount',{})))
    result={}
    for row in rows:
        context=contexts.get(row.id)
        if context:
            status,tool=context.tool_status,context.tool_no
        else:
            facts={(m.get('status','unknown') if not m.get('operation') and not m.get('requires_confirmation') else 'unknown',m.get('tool_no')) for mid,m in evidence[row.id] if mid==row.machine_id}
            status,tool=next(iter(facts)) if len(facts)==1 else ('unknown',None)
        waiting=status=='mounted'
        code=context.reason_code if context else None
        reason=WAIT_REASONS.get(code,'Nicht erfasst')
        label=('Gerüstet · wartet auf Produktionsstart' if row.order_id else 'Gerüstet · keine aktive Produktion') if waiting else 'Abgerüstet · ohne Werkzeug' if status=='empty' else 'Keine aktive Tätigkeit · Werkzeugzustand ungeklärt'
        seconds=max(0,((row.end_time or now)-row.start_time).total_seconds())
        since=row.start_time
        if waiting and not row.end_time:
            # A reason change splits the accounting interval, not the idle spell.
            for _ in range(50):
                if (now-since).total_seconds()>=300:break
                prior=TimeBooking.query.filter_by(machine_id=row.machine_id,process='FREI',order_id=row.order_id,end_time=since).filter(TimeBooking.start_time<since).all()
                if len(prior)!=1 or not prior[0].idle_context or prior[0].idle_context.tool_status!='mounted' or prior[0].idle_context.tool_no!=tool:break
                since=prior[0].start_time
        hint=(f'Seit mindestens 5 Minuten gerüstet ohne Produktion. Wartegrund: {reason}. Produktionsstart oder weiteren Ablauf prüfen.' if waiting and not row.end_time and (now-since).total_seconds()>=300 else '')
        result[row.id]=dict(label=label,tool_no=tool,tool_status=status,waiting=waiting,
            reason=reason,reason_code=code,note=context.reason_note if context else None,
            evidence='Bei Buchung erfasst' if context else 'Aus damaligem Befehlsprotokoll' if status!='unknown' else 'Historisch nicht belegt',
            seconds=seconds,hint=hint)
    return result

def time_summary(bookings, views, *, now=None, start=None, end=None, calendar=None, exceptions=None):
    from .order_statistics import merged, working_seconds
    now=now or datetime.utcnow()
    groups=defaultdict(list); all_intervals=defaultdict(list); reasons=defaultdict(list)
    labels={'ABRUEST':'Abrüstzeit','RUEST':'Rüstzeit','waiting':'Gerüstete Wartezeit',
        'empty':'Abgerüsteter Leerlauf','unknown':'Ungeklärter Leerlauf',
        'PROD':'Produktionszeit','MUSTER':'Musterungszeit','other':'Unterbrechungen / weitere Tätigkeiten'}
    for row in bookings:
        first=max(row.start_time,start) if start else row.start_time
        last=min(row.end_time or now,now,end or now)
        if last<=first or row.type=='STORNO':continue
        info=views.get(row.id,{})
        group=('waiting' if info.get('waiting') else 'empty' if info.get('tool_status')=='empty' else 'unknown') if row.process=='FREI' else row.process if row.process in labels else 'other'
        groups[(group,row.machine_id)].append((first,last));all_intervals[row.machine_id].append((first,last))
        if group=='waiting':reasons[(info['reason'],row.machine_id)].append((first,last))
    def seconds(intervals):
        return working_seconds(intervals,calendar,exceptions or []) if calendar else sum((b-a).total_seconds() for a,b in merged(intervals))
    totals={key:sum(seconds(v) for (group,_),v in groups.items() if group==key) for key in labels}
    overlap=sum(sum((b-a).total_seconds() for a,b in v)-sum((b-a).total_seconds() for a,b in merged(v)) for v in all_intervals.values())
    reason_totals={key:sum(seconds(v) for (reason,_),v in reasons.items() if reason==key) for key,_ in reasons}
    return dict(cards=[dict(key=key,label=label,seconds=totals[key]) for key,label in labels.items()],
                reasons=sorted(reason_totals.items()),overlap=overlap)
