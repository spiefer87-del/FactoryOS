from datetime import datetime
from pathlib import Path
from uuid import uuid4
from flask import Blueprint,render_template,request,redirect,url_for,abort,flash,current_app,send_file
from flask_login import login_required,current_user
from sqlalchemy.orm.exc import StaleDataError
from factoryos.extensions import db
from factoryos.core.auth import permission_required
from factoryos.core.access_control import valid_csrf
from factoryos.core.models.change_log import ChangeLog
from factoryos.modules.masterdata.articles.models import Article
from factoryos.modules.quality.inspection_plan.visual_presets import VISUAL_PRESETS
from .models import ArticleDefect,ArticleDefectPhoto
from .photos import prepare_photo

bp=Blueprint('article_defects',__name__,url_prefix='/quality/defect-catalog')
TYPES=[row[1] for row in VISUAL_PRESETS]+['Sonstiger Produktionsfehler']

def photo_root():return Path(current_app.instance_path)/'article_defect_photos'

@bp.get('/')
@login_required
@permission_required('defects.view')
def overview():
    article_id=request.args.get('article_id',type=int)
    query=ArticleDefect.query
    if article_id:query=query.filter_by(article_id=article_id)
    return render_template('article_defects/list.html',entries=query.order_by(ArticleDefect.created_at.desc(),ArticleDefect.id.desc()).all(),article_id=article_id)

@bp.get('/<int:entry_id>')
@login_required
@permission_required('defects.view')
def detail(entry_id):return render_template('article_defects/detail.html',entry=ArticleDefect.query.get_or_404(entry_id))

@bp.get('/photo/<int:photo_id>')
@login_required
@permission_required('defects.view')
def photo(photo_id):
    row=ArticleDefectPhoto.query.get_or_404(photo_id)
    if Path(row.filename).name!=row.filename:abort(404)
    path=photo_root()/row.filename
    if not path.is_file():abort(404)
    response=send_file(path,mimetype='image/jpeg',conditional=True)
    response.headers['Cache-Control']='private, no-store';response.headers['X-Content-Type-Options']='nosniff'
    return response

def form(entry=None):
    values=dict(article_id=str(entry.article_id) if entry else request.args.get('article_id',''),title=entry.title if entry else '',defect_type=entry.defect_type if entry else '',description=entry.description if entry else '',remedy=entry.remedy if entry else '',archived='yes' if entry and entry.archived else '')
    error=None;status=200;written=[]
    if request.method=='POST':
        if not valid_csrf():abort(400,'Formular abgelaufen. Bitte neu laden.')
        values={key:request.form.get(key,'').strip() for key in values}
        try:
            if not values['article_id'].isdigit():raise ValueError('Artikel: vorhandenen Stammdatenartikel auswählen.')
            article=db.session.get(Article,int(values['article_id']))
            if not article:raise ValueError('Artikel: vorhandenen Stammdatenartikel auswählen.')
            if entry and article.id!=entry.article_id:raise ValueError('Artikelzuordnung darf nach Erfassung nicht geändert werden.')
            for key,label,limit,required in [('title','Kurzbeschreibung',200,True),('description','Fehlerbeschreibung',5000,True),('remedy','Erprobte Abhilfe / Hinweise',5000,False)]:
                if (required and not values[key]) or len(values[key])>limit:raise ValueError(f'{label}: bitte ausfüllen, maximal {limit} Zeichen.')
            if values['defect_type'] not in TYPES:raise ValueError('Fehlerart: bitte einen Eintrag aus der Auswahl verwenden.')
            if entry and str(entry.version)!=request.form.get('version'):raise StaleDataError()
            uploads=[f for f in request.files.getlist('photo')+request.files.getlist('camera') if f and f.filename]
            if len(uploads)+(len(entry.photos) if entry else 0)>5:raise ValueError('Fotos: maximal fünf Bilder pro Fehler.')
            prepared=[prepare_photo(upload.stream) for upload in uploads]
            is_new=entry is None
            if is_new:entry=ArticleDefect(article_id=article.id,created_by_id=current_user.id);db.session.add(entry)
            entry.title=values['title'];entry.defect_type=values['defect_type'];entry.description=values['description'];entry.remedy=values['remedy'];entry.archived=values['archived']=='yes';entry.updated_at=datetime.utcnow()
            db.session.flush()
            if prepared:photo_root().mkdir(parents=True,exist_ok=True,mode=0o700)
            for raw in prepared:
                name=uuid4().hex+'.jpg';target=photo_root()/name
                with target.open('xb') as stream:stream.write(raw)
                written.append(target);db.session.add(ArticleDefectPhoto(defect_id=entry.id,filename=name))
            db.session.add(ChangeLog(entity_type='article',entity_id=article.id,entity_name=article.article_no,action='create' if is_new else 'update',category='article_defect',user_id=current_user.id,changes={'defect_catalog':{'old':None,'new':{'entry_id':entry.id,'title':entry.title,'description':entry.description,'remedy':entry.remedy,'type':entry.defect_type,'archived':entry.archived,'new_photos':len(prepared)}}}))
            db.session.commit();flash('Artikelfehler gespeichert.','success');return redirect(url_for('article_defects.detail',entry_id=entry.id),code=303)
        except (ValueError,StaleDataError) as exc:
            db.session.rollback()
            for path in written:path.unlink(missing_ok=True)
            error='Dieser Eintrag wurde inzwischen geändert. Bitte neu laden.' if isinstance(exc,StaleDataError) else str(exc);status=409 if isinstance(exc,StaleDataError) else 422
        except Exception:
            db.session.rollback()
            for path in written:path.unlink(missing_ok=True)
            raise
    return render_template('article_defects/form.html',entry=entry,values=values,types=TYPES,articles=Article.query.order_by(Article.article_no).all(),error=error),status

@bp.route('/create',methods=['GET','POST'])
@login_required
@permission_required('defects.create')
def create():return form()

@bp.route('/<int:entry_id>/edit',methods=['GET','POST'])
@login_required
@permission_required('defects.edit')
def edit(entry_id):return form(ArticleDefect.query.get_or_404(entry_id))

