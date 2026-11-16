import copy
import json
from datetime import datetime
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, send_file, current_app
from itsdangerous import URLSafeSerializer, BadSignature
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from factoryos.extensions import db
from factoryos.core.auth import permission_required, has_permission
from factoryos.core.access_control import valid_csrf
from factoryos.modules.masterdata.tools.models import Tool
from ..models import SetupReport, SetupReportPhoto, SetupReportRevision
from ..schema import FIELDS, PROFILES, STEPS, UNITS, ORIGINS
from ..service import choices, make_context, initial_data, clean_data, gaps, snapshot
from ..validation import ReportValidationError, error_payload

bp=Blueprint("setup_reports",__name__,url_prefix="/masterdata/tools/<int:tool_id>/setup-reports")


def get_report(tool_id, report_id):
    return SetupReport.query.filter_by(id=report_id,tool_id=tool_id).first_or_404()


def csrf():
    if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden; ungespeicherte Angaben vorher sichern.")


def editable(report):
    if report.state!="draft":abort(409,"Abgeschlossener Bericht ist schreibgeschützt. Neue Fassung anlegen.")


def version(report, raw):
    try:valid=int(raw)==report.version
    except (TypeError,ValueError):valid=False
    if not valid:abort(409,"Bericht wurde inzwischen geändert. Bitte eigene Eingaben sichern und neu laden.")


def context_token(report, context):
    return URLSafeSerializer(current_app.secret_key,salt='setup-context-v1').dumps(dict(report=report.id,user=current_user.id,ids={key:context.get(key) for key in ('tool_id','machine_id','article_id','material_id','masterbatch_id')}))


@bp.after_request
def private(response):
    response.headers["Cache-Control"]="private, no-store"
    response.headers["X-Content-Type-Options"]="nosniff"
    return response


@bp.route("/")
@login_required
@permission_required("setup_reports.view")
def overview(tool_id):
    tool=Tool.query.get_or_404(tool_id)
    return render_template("setup_reports/overview.html",tool=tool,reports=SetupReport.query.filter_by(tool_id=tool_id).order_by(SetupReport.id.desc()).all())


@bp.route("/new",methods=["POST"])
@login_required
@permission_required("setup_reports.create")
def create(tool_id):
    csrf();tool=Tool.query.get_or_404(tool_id)
    context,values=make_context(tool,{})
    report=SetupReport(tool_id=tool_id,context=context,data=initial_data(values),created_by_id=current_user.id)
    previous=request.form.get("previous_id")
    if previous:
        if not has_permission(current_user,"setup_reports.view"):abort(403)
        try:prior=get_report(tool_id,int(previous))
        except ValueError:abort(400)
        report.previous_id=prior.id;report.context=copy.deepcopy(prior.context)
        report.data=copy.deepcopy(prior.data);report.data["context_confirmed"]=False
        for item in report.data.get("values",{}).values():
            item.update(status="open",origin="previous",photo_id=None,evidence=f"Vorlage Bericht #{prior.id}, Stand {prior.version} - erneut prüfen")
        for item in report.data.get("profiles",{}).values():item.update(status="open",origin="previous",photo_id=None)
    db.session.add(report);snapshot(report,"Einstellbericht angelegt");db.session.commit()
    return redirect(url_for("setup_reports.detail",tool_id=tool_id,report_id=report.id))


@bp.route("/<int:report_id>")
@login_required
@permission_required("setup_reports.view")
def detail(tool_id,report_id):
    report=get_report(tool_id,report_id)
    is_editable=report.state=="draft" and has_permission(current_user,"setup_reports.edit")
    from ..external_vision import public_status
    boot=dict(report_id=report.id,version=report.version,context=report.context,context_token=context_token(report,report.context),data=report.data,
        fields=FIELDS,profiles=PROFILES,steps=STEPS,units=UNITS,origins=ORIGINS,
        editable=is_editable,choices=choices(report.tool) if is_editable else {},
        external_vision={**public_status(),"allowed":is_editable and has_permission(current_user,"setup_reports.external_ocr")},
        context_url=url_for("setup_reports.context",tool_id=tool_id,report_id=report.id),
        photo_url=url_for("setup_reports.scan",tool_id=tool_id,report_id=report.id),
        photo_base=url_for("setup_reports.photo",tool_id=tool_id,report_id=report.id,photo_id=0),
        save_url=url_for("setup_reports.save",tool_id=tool_id,report_id=report.id))
    return render_template("setup_reports/wizard.html",report=report,boot=boot,gaps=gaps(report),can_release=has_permission(current_user,'setup_reports.release'),
        photos=SetupReportPhoto.query.filter_by(report_id=report.id).all(),
        revisions=SetupReportRevision.query.filter_by(report_id=report.id).order_by(SetupReportRevision.version.desc()).all())


@bp.route("/<int:report_id>/context",methods=["POST"])
@login_required
@permission_required("setup_reports.edit")
def context(tool_id,report_id):
    csrf();report=get_report(tool_id,report_id);editable(report)
    if request.content_length and request.content_length>8000:abort(413)
    try:
        ids=request.get_json().get("ids",{});context,values=make_context(report.tool,ids)
        return jsonify(context=context,context_token=context_token(report,context),values=values,choices=choices(report.tool))
    except (ValueError,AttributeError) as error:return jsonify(error_payload(error)),400


@bp.route("/<int:report_id>/save",methods=["POST"])
@login_required
@permission_required("setup_reports.edit")
def save(tool_id,report_id):
    csrf();report=get_report(tool_id,report_id);editable(report)
    if request.content_length and request.content_length>220000:abort(413)
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict):abort(400)
    if 'release' in payload and not isinstance(payload['release'],bool):abort(400)
    version(report,payload.get("version"))
    if payload.get("release") and not has_permission(current_user,"setup_reports.release"):abort(403)
    try:
        context,suggestions=make_context(report.tool,payload.get("ids",{}))
        try:
            serializer=URLSafeSerializer(current_app.secret_key,salt='setup-context-v1')
            preview=serializer.loads(payload.get('context_token',''))
            if preview!=serializer.loads(context_token(report,context)):
                raise ReportValidationError('Zuordnungen wurden geändert. Bitte Stammdatenvorschläge laden und erneut bestätigen.',context='context_confirmed')
        except BadSignature:
            raise ReportValidationError('Stammdatenvorschläge bitte zuerst laden und Zuordnungen bestätigen.',context='context_confirmed')
        data=clean_data(report,payload.get("data"),suggestions)
        report.context=context;report.data=data;report.updated_at=datetime.utcnow()
        if payload.get("release"):
            missing=gaps(report)
            if missing:
                db.session.rollback();return jsonify(error="Bericht ist noch nicht vollständig geprüft.",gaps=missing),422
            report.state="released";report.released_by_id=current_user.id;report.released_at=datetime.utcnow()
        snapshot(report,"Einstellbericht abgeschlossen" if payload.get("release") else "Einstellbericht gespeichert")
        db.session.commit()
        return jsonify(version=report.version,data=report.data,context=report.context,state=report.state,gaps=gaps(report))
    except ValueError as error:
        db.session.rollback();return jsonify(error_payload(error)),400
    except (IntegrityError,StaleDataError):
        db.session.rollback();return jsonify(error="Zwischenzeitliche Änderung. Eigene Eingaben sichern, dann neu laden."),409


@bp.route("/<int:report_id>/scan",methods=["POST"])
@login_required
@permission_required("setup_reports.edit")
def scan(tool_id,report_id):
    csrf();report=get_report(tool_id,report_id);editable(report)
    version(report,request.form.get("version"))
    provider=request.form.get("provider","local")
    if provider not in ("local","groq"):abort(400)
    if provider=="groq":
        if not has_permission(current_user,"setup_reports.external_ocr"):abort(403)
        if request.form.get("external_consent")!="yes":return jsonify(error="Fotoübertragung an Groq bitte für dieses Foto ausdrücklich bestätigen."),400
    elif SetupReportPhoto.query.filter_by(report_id=report.id).count()>=12:return jsonify(error="Maximal 12 Fotos je Bericht. Weitere Angaben manuell ergänzen oder neue Fassung anlegen."),400
    if request.content_length and request.content_length>11*1024*1024:abort(413)
    upload=request.files.get("photo")
    if not upload:return jsonify(error="Bitte ein Foto aufnehmen oder auswählen."),400
    profile=request.form.get("profile","unknown")
    if profile not in ("nc5","unknown"):abort(400)
    from ..ocr import read_screen
    from factoryos.modules.masterdata.materials.services.material_scan_service import ScanUnavailable,ScanBusy
    try:
        raw=upload.stream.read(10*1024*1024+1)
        if provider=="groq":
            from ..external_vision import read_external
            image,result,cached=read_external(raw,request.form.get("step"),profile,report)
            if cached:
                return jsonify(result=result,photo_id=cached.id,version=report.version,cached=True,url=url_for("setup_reports.photo",tool_id=tool_id,report_id=report.id,photo_id=cached.id))
        else:image,result=read_screen(raw,profile)
        photo=SetupReportPhoto(report_id=report.id,actor_id=current_user.id,image=image,text=result["text"],result=result)
        # Serialize photo additions with saves using the report's optimistic version.
        report.updated_at=datetime.utcnow();db.session.add(photo)
        snapshot(report,"Bildschirmfoto hinzugefügt");db.session.commit()
        return jsonify(result=result,photo_id=photo.id,version=report.version,url=url_for("setup_reports.photo",tool_id=tool_id,report_id=report.id,photo_id=photo.id))
    except ScanBusy as error:db.session.rollback();return jsonify(error=str(error)),429
    except ScanUnavailable as error:db.session.rollback();return jsonify(error=str(error)),503
    except ValueError as error:db.session.rollback();return jsonify(error=str(error)),400
    except (IntegrityError,StaleDataError):db.session.rollback();return jsonify(error="Bericht wurde inzwischen geändert. Bitte neu laden."),409


@bp.route("/<int:report_id>/photos/<int:photo_id>")
@login_required
@permission_required("setup_reports.view")
def photo(tool_id,report_id,photo_id):
    get_report(tool_id,report_id)
    picture=SetupReportPhoto.query.filter_by(report_id=report_id,id=photo_id).first_or_404()
    return send_file(BytesIO(picture.image),mimetype="image/jpeg",max_age=0)


@bp.route("/<int:report_id>/pdf")
@login_required
@permission_required("setup_reports.pdf_export")
def pdf(tool_id,report_id):
    report=get_report(tool_id,report_id)
    from ..pdf_service import build_pdf
    return send_file(BytesIO(build_pdf(report)),mimetype="application/pdf",as_attachment=True,
        download_name=f"Einstellbericht_{report.id}_Stand_{report.version}.pdf",max_age=0)


@bp.route("/<int:report_id>/history/<int:revision>")
@login_required
@permission_required("setup_reports.view")
def history(tool_id,report_id,revision):
    report=get_report(tool_id,report_id)
    record=SetupReportRevision.query.filter_by(report_id=report_id,version=revision).first_or_404()
    return render_template("setup_reports/history.html",report=report,revision=record,fields=FIELDS,profiles=PROFILES,origins=ORIGINS)
