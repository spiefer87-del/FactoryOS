"""Read existing QM and warehouse journals without copying their records."""
from types import SimpleNamespace
from flask_login import current_user
from sqlalchemy.orm import joinedload, selectinload
from factoryos.core.auth import has_permission
from factoryos.models.user import User
from factoryos.extensions import db
from factoryos.core.models.change_log import ChangeLog


def supplemental_activity(entity_type, count, inspector):
    logs=[];available=[]
    def take(query):return query.limit(count).all() if count else query.all()
    if has_permission(current_user,'quality.view') and inspector.has_table('gauge') and inspector.has_table('gauge_calibration'):
        available.append('gauge')
        if entity_type in (None,'','gauge'):
            from factoryos.modules.quality.gauges.models import GaugeCalibration as Calibration
            ref=ChangeLog.changes['calibration_id'].as_integer()
            recorded=db.select(ref).where(ChangeLog.entity_type=='gauge',ChangeLog.action=='calibration',ref.isnot(None))
            query=Calibration.query.filter(Calibration.id.notin_(recorded)).options(joinedload(Calibration.gauge)).order_by(Calibration.created_at.desc(),Calibration.id.desc())
            for row in take(query):
                logs.append(SimpleNamespace(id=row.id,entity_type='gauge',entity_id=row.gauge_id,
                    entity_name=row.gauge.gauge_no if row.gauge else f'#{row.gauge_id}',action='calibration',category='quality',
                    changes=dict(calibration_id=row.id,calibration_date=row.calibration_date.isoformat() if row.calibration_date else None,
                        next_calibration=row.next_calibration.isoformat() if row.next_calibration else None,
                        result=row.result,certificate_no=row.certificate_no,note=row.note),
                    user=None,actor_label='Nicht protokolliert (älterer Kalibriereintrag)',
                    created_at=row.created_at,source='calibration_journal'))
    if has_permission(current_user,'quality.view') and all(inspector.has_table(name) for name in ('qm_change_logs','qm_plans','qm_plan_versions')):
        available.append('qm_plan')
        if entity_type in (None,'','qm_plan'):
            from factoryos.modules.quality.inspection_plan.models import QualityInspectionChangeLog as Audit, QualityInspectionPlan as Plan
            query=Audit.query.options(joinedload(Audit.user)).order_by(Audit.created_at.desc(),Audit.id.desc())
            rows=take(query)
            plans={row.id:row for row in Plan.query.filter(Plan.id.in_({r.plan_id for r in rows})).options(joinedload(Plan.article),joinedload(Plan.tool)).all()} if rows else {}
            for row in rows:
                plan=plans.get(row.plan_id)
                name=f'{plan.article.article_no} · {plan.tool.tool_no}' if plan and plan.article and plan.tool else f'#{row.plan_id}'
                logs.append(SimpleNamespace(id=row.id,entity_type='qm_plan',entity_id=row.plan_id,entity_name=name,
                    action='update',category='qm_plan',changes={'message':row.message},user=row.user,
                    created_at=row.created_at,source='qm_journal'))
    if has_permission(current_user,'inventory.view') and all(inspector.has_table(name) for name in ('warehouse_events','warehouse_lots','warehouse_lines','warehouse_locations')):
        available.append('inventory')
        if entity_type in (None,'','inventory'):
            from factoryos.modules.inventory.models import WarehouseEvent as Event,WarehouseLot as Lot,WarehouseLocation as Location
            from factoryos.modules.inventory.service import LABELS
            rows=take(Event.query.options(selectinload(Event.lines)).order_by(Event.created_at.desc(),Event.id.desc()))
            lots={row.id:row for row in Lot.query.filter(Lot.id.in_({r.lot_id for r in rows})).all()} if rows else {}
            users={row.id:row for row in User.query.filter(User.id.in_({r.user_id for r in rows})).all()} if rows else {}
            locations={row.id:row.code for row in Location.query.all()} if rows else {}
            for row in rows:
                lot=lots.get(row.lot_id);data=row.details or {}
                changes={'quantity':row.quantity,'reason':row.reason}
                if lot:changes.update(article_no=lot.article_no,article_name=lot.article_name,batch=lot.batch,order_no=lot.order_no)
                for key in ('code','description','reference'):
                    if data.get(key):changes[key]=data[key]
                for key in ('location_id','destination_id'):
                    if data.get(key):
                        try:changes[key]=locations.get(int(data[key]),'Nicht mehr vorhanden')
                        except (TypeError,ValueError):pass
                if row.lines:
                    changes['stock_lines']=[dict(location=locations.get(line.location_id,'Nicht mehr vorhanden'),status=line.status,quantity=line.quantity) for line in row.lines]
                logs.append(SimpleNamespace(id=row.id,entity_type='inventory',entity_id=row.id,
                    entity_name=lot.article_no if lot else data.get('code') or f'Buchung #{row.id}',
                    action=row.kind,action_label={'location':'Lagerplatz angelegt','transfer':'Produktionsübergabe erfasst','receive':'Lagerannahme gebucht','cancel':'Übergabe storniert','reject':'Ausschuss vor Lagerannahme gebucht','opening':'Erstbestand erfasst','move':'Bestand umgelagert','block':'Bestand gesperrt','release':'Bestand freigegeben','scrap':'Lagerausschuss gebucht','reserve':'Bestand reserviert','pick':'Kommissionierung bestätigt','ship':'Versand bestätigt','unreserve':'Reservierung freigegeben','return':'Rücknahme erfasst','reverse':'Gegenbuchung erfasst'}.get(row.kind,LABELS.get(row.kind,'Lagerbuchung')),category='warehouse',
                    changes=changes,user=users.get(row.user_id),created_at=row.created_at,source='warehouse_journal'))
    return logs,available
