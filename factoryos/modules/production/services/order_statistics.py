"""Read-only order statistics. Reported facts and nominal estimates stay separate."""
from datetime import datetime, timedelta, timezone
from math import ceil, floor, isfinite
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from factoryos.extensions import db
from factoryos.modules.orders.services.cycle_time import valid_cycle_time
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.masterdata.tools.models import Tool
from factoryos.modules.production.models import TimeBooking, QuantityReport, ProductionCalendarSettings
from .calendar_service import calculate_production_finish, get_calendar_exceptions, get_non_working_periods

LOCAL_ZONE = ZoneInfo("Europe/Berlin")
PRODUCTION = ("PROD", "MUSTER")

def local_time(value):
    return value.replace(tzinfo=timezone.utc).astimezone(LOCAL_ZONE) if value else None

def local_label(value):
    stamp = local_time(value)
    return stamp.strftime("%d.%m.%Y %H:%M:%S %Z") if stamp else "Noch nicht erfasst"

def duration(seconds):
    if seconds is None: return "Nicht berechenbar"
    if 0 <= seconds < 60: return f"{max(0,round(seconds))} Sek"
    minutes = max(0, round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return ((f"{days} T " if days else "") + (f"{hours} Std " if hours else "") + f"{minutes} Min").strip()

def positive(value):
    try:
        number = float(value)
        return number if isfinite(number) and number > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None

def count(value):
    number = positive(value)
    return int(number) if number is not None and number.is_integer() else 0

def merged(intervals):
    result = []
    for start, end in sorted((start,end) for start,end in intervals if end > start):
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else: result.append((start,end))
    return result

def working_seconds(intervals, settings, exceptions):
    seconds = 0
    for start, end in merged(intervals):
        seconds += (end-start).total_seconds()
        for closure in get_non_working_periods(start,end,settings,exceptions):
            seconds -= (closure[1]-closure[0]).total_seconds()
    return max(0, seconds)

def forecast_data(order, good, article, tool, now, settings, exceptions, elapsed=0):
    if order.is_project: return None
    target = count(order.target_qty)
    cycle = valid_cycle_time(order.cycle_time_s)
    source = "Auftragssollwert"
    if cycle is None:
        cycle = valid_cycle_time(article.cycle_time_s) if article else None
        source = "Artikelwert für Altauftrag (nicht am Auftrag gesichert)"
    if not cycle or target <= 0: return None
    cavities = count(getattr(tool,"cavities",None)) or 1
    assumed = not count(getattr(tool,"cavities",None))
    remaining = max(0, target-good)
    seconds = max(0, ceil(remaining/cavities)*cycle - elapsed)
    if not isfinite(seconds): return None
    try: end = calculate_production_finish(now,seconds,settings,exceptions)
    except (ValueError,RuntimeError,OverflowError): return None
    delay = max(0,(end-now).total_seconds()-seconds)
    estimate = min(target, good + floor(max(0,elapsed)/cycle)*cavities)
    return dict(at=end, target_qty=target, good_qty=good, remaining_qty=remaining,
                estimated_good_qty=estimate, estimated_remaining_qty=max(0,target-estimate),
                cycle_time_s=cycle, cycle_source=source, parts_per_cycle=cavities,
                cavities_assumed=assumed, remaining_cycles=ceil(seconds/cycle),
                remaining_seconds=seconds,duration_label=duration(seconds),
                calendar_delay_seconds=delay,calendar_delay_label=duration(delay),
                nominal_elapsed_seconds=elapsed,tool_source="Werkzeugstamm" if tool else "Kein eindeutiges Werkzeug")

def order_statistics(order, now=None, settings=None, exceptions=None):
    now = now or datetime.utcnow()
    settings = settings or ProductionCalendarSettings.query.first() or SimpleNamespace(
        week_start_day=0,week_start_time="04:30",week_end_day=5,week_end_time="06:00")
    exceptions = get_calendar_exceptions() if exceptions is None else exceptions
    bookings = (TimeBooking.query.options(joinedload(TimeBooking.machine))
                .filter_by(order_id=order.id).order_by(TimeBooking.start_time,TimeBooking.id).all())
    production = [booking for booking in bookings if booking.process in PRODUCTION]
    active = [booking for booking in production if booking.end_time is None]
    complete = (order.status or "").lower() in ("finished","fertig") or bool(order.sampling and order.sampling.state=="completed")
    intervals = merged([(booking.start_time,min(booking.end_time or now,now))
                        for booking in production if booking.start_time <= now])
    gross = sum((end-start).total_seconds() for start,end in intervals)
    net = working_seconds(intervals,settings,exceptions)
    quantities = db.session.query(func.count(QuantityReport.id),
        func.coalesce(func.sum(QuantityReport.good_qty),0),
        func.coalesce(func.sum(QuantityReport.scrap_qty),0),func.max(QuantityReport.created_at)
        ).filter(QuantityReport.order_id==order.id).one()
    reports, good, scrap, last_report = quantities
    good, scrap = count(good), count(scrap)
    target = count(order.target_qty)
    article = order.sampling.article if order.sampling else Article.query.options(joinedload(Article.tools),joinedload(Article.masterbatch)).filter_by(article_no=order.article or "").first()
    number = ((active[0].tool_no if len(active)==1 else None) or order.tool_no or "").strip()
    tool = Tool.query.filter_by(tool_no=number).first() if number else None
    if not tool and not number and order.sampling: tool = order.sampling.tool
    if not tool and not number and article and len(article.tools)==1: tool=article.tools[0]
    anchor = last_report if reports else (intervals[0][0] if intervals else now)
    anchor_intervals = [(max(start,anchor),end) for start,end in intervals if end>anchor]
    elapsed = working_seconds(anchor_intervals,settings,exceptions)
    forecast = forecast_data(order,good,article,tool,now,settings,exceptions,elapsed)
    issues = []
    if complete and active: issues.append("Abgeschlossener Auftrag hat noch eine aktive Buchung. Bitte Buchungsstand prüfen.")
    if len(active)>1: issues.append("Mehrere Produktionsbuchungen laufen parallel. Endprognose bitte erst nach Buchungskorrektur verwenden.")
    if not forecast: issues.append("Keine Laufzeitprognose: gültige Soll-Zykluszeit oder Sollstückzahl fehlt.")
    elif forecast["cavities_assumed"]: issues.append("Vorläufige Schätzung mit 1 Teil je Zyklus: Werkzeugkavitäten fehlen.")
    if forecast and forecast["remaining_seconds"]==0 and good<target:
        issues.append("Rechnerisches Sollende erreicht. Gutmenge und tatsächlichen Auftragsabschluss bitte bestätigen.")
    if last_report and last_report>now: issues.append("Die letzte Mengenmeldung liegt in der Zukunft. Zeitbasis prüfen.")
    planned = forecast_data(order,0,article,tool,now,settings,exceptions,0)
    cavities = forecast["parts_per_cycle"] if forecast else (count(getattr(tool,"cavities",None)) or 1)
    shot = positive(article.shot_weight_g) if article else None
    shot_source = "Aktueller Artikelstamm"
    if order.sampling:
        data = order.sampling.data or {}
        reference = (order.sampling.snapshot or {}).get("reference",{})
        shot = positive(data.get("shot_weight")) or positive(reference.get("Schussgewicht laut Artikel (g)"))
        shot_source = "Musterungsangabe / gespeicherte Artikelreferenz"
        percent = data.get("masterbatch_percent")
        has_batch = bool(data.get("masterbatch_id") or data.get("masterbatch"))
    else:
        percent = article.masterbatch_percent if article else None
        has_batch = bool(article and article.masterbatch_id)
    total_mass = ceil(target/cavities)*shot/1000 if shot and target else None
    remaining_mass = ceil(max(0,target-good)/cavities)*shot/1000 if shot and target else None
    consumed_estimate = ceil((good+scrap)/cavities)*shot/1000 if shot and reports else None
    total_mass = total_mass if total_mass is not None and isfinite(total_mass) else None
    remaining_mass = remaining_mass if remaining_mass is not None and isfinite(remaining_mass) else None
    consumed_estimate = consumed_estimate if consumed_estimate is not None and isfinite(consumed_estimate) else None
    material_label = "Kein auftragsbezogener Rohstoff hinterlegt"
    if order.sampling:
        material_ref=(order.sampling.snapshot or {}).get("material",{})
        material_label=" / ".join(str(material_ref.get(key)) for key in ("number","name") if material_ref.get(key)) or material_label
    elif order.erp_import:
        material_ref=(order.erp_import.snapshot or {}).get("references",{}).get("material",{})
        material_label=" / ".join(str(material_ref.get(key)) for key in ("number","name") if material_ref.get(key)) or material_label
        if article and article.material and material_ref.get("number") and material_ref["number"]!=article.material.material_no:
            issues.append("ERP-Rohstoff weicht vom aktuellen Artikelstamm ab. Materialrezept und Schussgewicht bitte fachlich prüfen.")
    elif article and article.material:
        material_label=f"{article.material.material_no} / {article.material.name} (Artikelvorschlag)"
    main, batch = None, None
    if total_mass is not None:
        if not has_batch: main,batch=total_mass,0
        elif percent is not None and positive(percent) is not None and float(percent)<=100:
            main = total_mass/(1+float(percent)/100);batch=total_mass-main
        elif percent==0: main,batch=total_mass,0
        else: issues.append("Farbbatch-Anteil fehlt: Hauptrohstoff und Batch können nicht getrennt geschätzt werden.")
    if not shot: issues.append("Materialbedarf nicht berechenbar: Schussgewicht in Gramm fehlt.")
    if order.is_project: issues.append("Projektauftrag: stückbezogene Produktionskennzahlen sind nicht anwendbar.")
    pause = sum(max(0,(min(booking.end_time or now,now)-booking.start_time).total_seconds())
                for booking in bookings if booking.process=="PAUSE")
    return dict(now=now,first_start=production[0].start_time if production else None,
        bookings=production,active_booking=active[0] if len(active)==1 else None,
        good=good,scrap=scrap,report_count=reports,last_report=last_report,
        target=target,remaining=max(0,target-good),progress=min(100,100*good/target) if target else None,
        scrap_percent=100*scrap/(good+scrap) if good+scrap else None,
        gross_seconds=gross,working_seconds=net,pause_seconds=pause,
        planned_seconds=planned["remaining_seconds"] if planned else None,
        forecast=forecast,eta=forecast["at"] if forecast and len(active)==1 and not complete else None,
        is_complete=complete,last_end=max((booking.end_time for booking in production if booking.end_time),default=None),
        forecast_basis="Solltempo seit letzter Mengenmeldung" if reports else "Solltempo seit erfasstem Produktionsstart – noch ohne Mengenmeldung",
        total_mass=total_mass,remaining_mass=remaining_mass,consumed_estimate=consumed_estimate,
        main_mass=main,batch_mass=batch,shot_weight=shot,shot_source=shot_source,
        material_label=material_label,issues=issues)
