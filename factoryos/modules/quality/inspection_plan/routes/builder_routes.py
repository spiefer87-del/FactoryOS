from flask import request, redirect, url_for, abort
from flask_login import login_required
from factoryos.extensions import db
from ..models import QualityInspectionSection, QualityInspectionCheck, QualityInspectionCharacteristic, QualityInspectionGaugeCheck
from ..services.builder_service import save_settings, save_check, changed, text, numeric, PlanValidation
from .version_routes import render_editor
from . import bp


def back(section):
    return redirect(url_for('inspection.quality_version_edit',plan_id=section.version.plan_id,version_id=section.version.id,_anchor='section-'+str(section.id)),code=303)


@bp.route('/section/<int:section_id>/settings',methods=['POST'])
@login_required
def quality_module_settings(section_id):
    section=QualityInspectionSection.query.get_or_404(section_id)
    try:
        save_settings(section,request.form);db.session.commit();return back(section)
    except PlanValidation as error:
        db.session.rollback();return render_editor(section.version,error.errors,dict(request.form),'settings-'+str(section.id),422)


@bp.route('/section/<int:section_id>/move',methods=['POST'])
@login_required
def quality_move_module(section_id):
    section=QualityInspectionSection.query.get_or_404(section_id)
    sections=sorted(section.version.sections,key=lambda s:(s.sort_order or 0,s.id))
    offset={'up':-1,'down':1}.get(request.form.get('direction'))
    if offset is None: abort(400)
    index=sections.index(section);other=index+offset
    if 0<=other<len(sections):
        sections[index],sections[other]=sections[other],sections[index]
        for position,item in enumerate(sections,1): item.sort_order=position
        changed(section.version,'MOVE_MODULE',f'Modul {section.title} verschoben');db.session.commit()
    return back(section)


@bp.route('/section/<int:section_id>/check',methods=['POST'])
@login_required
def quality_save_check(section_id):
    section=QualityInspectionSection.query.get_or_404(section_id)
    if section.section_type in ('dimension','gauge'): abort(400)
    check_id=request.form.get('check_id',type=int)
    check=QualityInspectionCheck.query.filter_by(id=check_id,section_id=section.id).first_or_404() if check_id else None
    try:
        save_check(section,request.form,check);db.session.commit();return back(section)
    except PlanValidation as error:
        db.session.rollback();return render_editor(section.version,error.errors,dict(request.form),'check-'+str(check.id if check else 'new-'+str(section.id)),422)


@bp.route('/check/<int:check_id>/delete',methods=['POST'])
@login_required
def quality_delete_check(check_id):
    check=QualityInspectionCheck.query.get_or_404(check_id);section=check.section
    changed(section.version,'DELETE_CHECK',f'Merkmal {check.name} entfernt');db.session.delete(check);db.session.commit();return back(section)


@bp.route('/section/<int:section_id>/characteristic',methods=['POST'])
@login_required
def quality_save_measurement(section_id):
    section=QualityInspectionSection.query.get_or_404(section_id)
    if section.section_type!='dimension': abort(400)
    char_id=request.form.get('characteristic_id',type=int)
    char=QualityInspectionCharacteristic.query.filter_by(id=char_id,section_id=section.id).first_or_404() if char_id else None
    errors={}
    values={key:text(request.form,key,label,limit,errors,True) for key,label,limit in (
        ('name','Merkmal',200),('target_value','Sollwert',50),('tolerance_minus','Toleranz minus',50),('tolerance_plus','Toleranz plus',50),('unit','Einheit',20))}
    for key in ('tolerance_minus','tolerance_plus'):numeric(values[key],key,key,errors)
    if errors:return render_editor(section.version,errors,dict(request.form),'measurement-'+str(char.id if char else 'new-'+str(section.id)),422)
    if not char:
        char=QualityInspectionCharacteristic(section=section,sort_order=max([c.sort_order or 0 for c in section.characteristics]+[0])+1);db.session.add(char)
    for key,value in values.items():setattr(char,key,value)
    changed(section.version,'SAVE_MEASUREMENT',f'Prüfmaß {char.name} gespeichert');db.session.commit();return back(section)


@bp.route('/section/<int:section_id>/gauge',methods=['POST'])
@login_required
def quality_save_gauge(section_id):
    from factoryos.modules.quality.gauges.models import Gauge
    section=QualityInspectionSection.query.get_or_404(section_id)
    if section.section_type!='gauge':abort(400)
    check_id=request.form.get('gauge_check_id',type=int)
    check=QualityInspectionGaugeCheck.query.filter_by(id=check_id,section_id=section.id).first_or_404() if check_id else None
    errors={};name=text(request.form,'name','Merkmal',200,errors,True);method=text(request.form,'method','Methode / Annahmekriterium',200,errors,True)
    gauge=Gauge.query.filter_by(id=request.form.get('gauge_id',type=int),status='active').first()
    if not gauge:errors['gauge_id']='Prüfmittel: Bitte ein aktives Prüfmittel aus dem Stamm auswählen.'
    if errors:return render_editor(section.version,errors,dict(request.form),'gauge-'+str(check.id if check else 'new-'+str(section.id)),422)
    if not check:
        check=QualityInspectionGaugeCheck(section=section,sort_order=max([c.sort_order or 0 for c in section.gauge_checks]+[0])+1);db.session.add(check)
    check.name=name;check.method=method;check.gauge_id=gauge.id
    changed(section.version,'SAVE_GAUGE',f'Lehrenmerkmal {name} gespeichert');db.session.commit();return back(section)


@bp.route('/gauge-check/<int:gauge_check_id>/delete',methods=['POST'])
@login_required
def quality_delete_gauge_check(gauge_check_id):
    check=QualityInspectionGaugeCheck.query.get_or_404(gauge_check_id);section=check.section
    changed(section.version,'DELETE_GAUGE',f'Lehrenmerkmal {check.name} entfernt');db.session.delete(check);db.session.commit();return back(section)
