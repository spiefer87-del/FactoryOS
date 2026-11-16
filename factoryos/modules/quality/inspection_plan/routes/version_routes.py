from flask import render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from factoryos.extensions import db
from factoryos.core.access_control import allowed
from ..models import QualityInspectionPlanVersion
from ..definitions import MODULES, STATUS_LABELS
from ..services.section_service import add_section
from ..services.revision_service import create_new_revision
from ..services.builder_service import revision_token, workflow, readiness_errors, PlanValidation
from factoryos.modules.quality.gauges.models import Gauge
from . import bp
from ..visual_presets import visual_presets


def render_editor(version, errors=None, form_data=None, form_id=None, status=200):
    latest=max(version.plan.versions,key=lambda v:v.id)
    editable=version.status=='draft' and latest.id==version.id and allowed('quality.inspect')
    targets={}
    for key in errors or {}:
        if form_id: targets[key]=form_id+'-'+key
        elif key.startswith('section-'):targets[key]='-'.join(key.split('-')[:2])
        elif key.startswith('characteristic-'):targets[key]=key.replace('characteristic-','measurement-')
        else:targets[key]=key
    return render_template('quality/inspection_plan/version_editor.html', version=version,
        gauges=Gauge.query.filter_by(status='active').order_by(Gauge.gauge_no).all(),
        modules=MODULES, visual_presets=visual_presets(), status_labels=STATUS_LABELS, editable=editable, is_current=latest.id==version.id,
        revision_token=revision_token(version), readiness=readiness_errors(version),
        errors=errors or {}, error_targets=targets, form_data=form_data or {}, form_id=form_id,
        can_workflow=latest.id==version.id and allowed('quality.inspect')),status


@bp.route('/<int:plan_id>/version/<int:version_id>/edit', methods=['GET','POST'])
@login_required
def quality_version_edit(plan_id,version_id):
    version=QualityInspectionPlanVersion.query.filter_by(id=version_id,plan_id=plan_id).first_or_404()
    if request.method=='POST':
        try:
            add_type=request.form.get('add_section_type')
            if add_type:
                if version.status!='draft': abort(409,'Diese Revision ist für Änderungen gesperrt.')
                if add_type not in MODULES: raise PlanValidation({'module':'Unbekanntes Prüfmodul.'})
                add_section(version,add_type)
            else:
                workflow(version,request.form.get('workflow_action'))
                db.session.commit()
            return redirect(request.url,code=303)
        except PlanValidation as error:
            db.session.rollback()
            return render_editor(version,error.errors,dict(request.form),status=422)
    return render_editor(version)


@bp.route('/<int:version_id>/new_revision',methods=['POST'])
@login_required
def quality_new_revision(version_id):
    version=QualityInspectionPlanVersion.query.get_or_404(version_id)
    if version.status not in ('released','closed'): abort(409,'Neue Revision erst nach Freigabe erstellen.')
    new_version=create_new_revision(version_id,current_user.id)
    return redirect(url_for('inspection.quality_version_edit',plan_id=new_version.plan_id,version_id=new_version.id),code=303)
