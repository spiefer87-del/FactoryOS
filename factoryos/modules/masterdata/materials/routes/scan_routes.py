from flask import request,jsonify,url_for,abort
from flask_login import login_required,current_user
from sqlalchemy import func,or_
from factoryos.core.auth import permission_required,has_permission
from factoryos.core.access_control import valid_csrf
from ..models import Material
from ..services.material_scan_service import read_label,parse_label,ScanUnavailable,ScanBusy,MAX_UPLOAD,MAX_TEXT
from . import bp

def with_duplicates(result):
    values={p["field"]:p["value"] for p in result["proposals"]}
    conditions=[]
    for field in ("external_material_no","name"):
        if values.get(field):conditions.append(func.lower(getattr(Material,field))==values[field].lower())
    existing=Material.query.filter(or_(*conditions)).limit(6).all() if conditions else []
    result["duplicates"]=[dict(name=m.name,material_no=m.material_no,url=url_for("materials.detail",material_id=m.id)) for m in existing[:5]] if has_permission(current_user,"materials.view") else []
    result["duplicate_count"]=len(existing)
    return result

@bp.route("/scan",methods=["POST"])
@login_required
@permission_required("materials.create")
def scan_label():
    if request.content_length and request.content_length>MAX_UPLOAD+1024*1024:
        return jsonify(error="Foto ist zu groß. Bitte maximal 10 MB hochladen."),413
    if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
    upload=request.files.get("photo")
    if not upload:return jsonify(error="Bitte zuerst ein Foto aufnehmen oder auswählen."),400
    try:
        text,readability,languages=read_label(upload.stream.read(MAX_UPLOAD+1))
        result=with_duplicates(parse_label(text))
        if readability is None or readability<60:
            for proposal in result["proposals"]:
                proposal["certainty"]="review"
                proposal["note"]=(proposal["note"]+" Niedrige OCR-Lesbarkeit: Zeichen besonders sorgfältig prüfen.").strip()
        result.update(readability=readability,languages=languages)
        return jsonify(result),200,{"Cache-Control":"no-store"}
    except ScanBusy as exc:return jsonify(error=str(exc)),429,{"Retry-After":"3","Cache-Control":"no-store"}
    except ScanUnavailable as exc:return jsonify(error=str(exc)),503,{"Cache-Control":"no-store"}
    except ValueError as exc:return jsonify(error=str(exc)),400,{"Cache-Control":"no-store"}

@bp.route("/scan/text",methods=["POST"])
@login_required
@permission_required("materials.create")
def scan_text():
    if request.content_length and request.content_length>MAX_TEXT*6+4096:return jsonify(error="Etiketttext ist zu lang."),413
    if not valid_csrf():abort(400,"Formular abgelaufen. Bitte neu laden.")
    try:return jsonify(with_duplicates(parse_label(request.form.get("text","")))),200,{"Cache-Control":"no-store"}
    except ValueError as exc:return jsonify(error=str(exc)),400,{"Cache-Control":"no-store"}
