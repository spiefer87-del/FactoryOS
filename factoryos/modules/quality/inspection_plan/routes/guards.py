"""All mutation paths, including legacy marker/upload routes, share a lock."""
from flask import request, abort, g
from flask_login import current_user
from factoryos.extensions import db
from factoryos.core.access_control import valid_csrf
from ..models import (QualityInspectionPlanVersion, QualityInspectionSection, QualityInspectionCheck,
    QualityInspectionCharacteristic, QualityInspectionGaugeCheck, QualityInspectionIdentificationImage, QualityInspectionDimensionSnippet)
from ..services.builder_service import revision_token
from . import bp


@bp.before_request
def guard_plan_mutation():
    if request.method not in ('POST','PUT','PATCH','DELETE') or not current_user.is_authenticated:return
    if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden; es wurde nichts gespeichert.')
    args=request.view_args or {};data=request.get_json(silent=True) if request.is_json else request.form
    data=data or {};version=None
    if 'version_id' in args: version=QualityInspectionPlanVersion.query.get_or_404(args['version_id'])
    elif 'section_id' in args or data.get('section_id'):
        version=QualityInspectionSection.query.get_or_404(args.get('section_id') or data.get('section_id')).version
    else:
        for key,model in (('image_id',QualityInspectionIdentificationImage),('snippet_id',QualityInspectionDimensionSnippet),('check_id',QualityInspectionCheck),('gauge_check_id',QualityInspectionGaugeCheck)):
            if key in args:version=model.query.get_or_404(args[key]).section.version;break
        if version is None and data.get('id') and request.is_json:
            version=QualityInspectionCharacteristic.query.get_or_404(data['id']).section.version
    if version is None:return
    db.session.execute(db.update(QualityInspectionPlanVersion).where(QualityInspectionPlanVersion.id==version.id).values(status=QualityInspectionPlanVersion.status))
    db.session.expire_all()
    g.qm_version_id=version.id
    if args.get('plan_id') is not None and version.plan_id!=args['plan_id']:abort(404)
    if version.id!=max(v.id for v in version.plan.versions):abort(409,'Historische Revision ist schreibgeschützt. Bitte die aktuelle Revision öffnen.')
    token=request.headers.get('X-QM-Revision') or data.get('revision_token')
    if not token or token!=revision_token(version):abort(409,'Der Prüfplan wurde zwischenzeitlich geändert. Bitte neu laden und Eingaben erneut prüfen.')
    workflow_endpoint=request.endpoint in ('inspection.quality_version_edit','inspection.quality_new_revision')
    if not workflow_endpoint and version.status!='draft':abort(409,'Diese Revision ist schreibgeschützt. Zur Bearbeitung zurückgeben oder neue Revision anlegen.')
    if not workflow_endpoint:
        from ..services.builder_service import changed
        changed(version,'EDIT_CONTENT','Modulinhalt bearbeitet')


@bp.after_request
def expose_current_revision(response):
    if request.is_json and response.status_code<400 and getattr(g,'qm_version_id',None):
        version=db.session.get(QualityInspectionPlanVersion,g.qm_version_id)
        response.headers['X-QM-Revision']=revision_token(version)
    return response
