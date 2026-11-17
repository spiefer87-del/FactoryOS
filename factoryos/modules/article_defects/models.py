from datetime import datetime
from factoryos.extensions import db

class ArticleDefect(db.Model):
    __tablename__='article_defects'
    id=db.Column(db.Integer,primary_key=True)
    article_id=db.Column(db.Integer,db.ForeignKey('articles.id'),nullable=False,index=True)
    title=db.Column(db.String(200),nullable=False)
    tool_no=db.Column(db.String(100),nullable=True)
    defect_type=db.Column(db.String(100),nullable=False)
    description=db.Column(db.Text,nullable=False)
    remedy=db.Column(db.Text,nullable=False,default='')
    archived=db.Column(db.Boolean,nullable=False,default=False)
    created_by_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    version=db.Column(db.Integer,nullable=False,default=1)
    __mapper_args__={'version_id_col':version}
    article=db.relationship('Article')
    author=db.relationship('User')
    photos=db.relationship('ArticleDefectPhoto',backref='defect',order_by='ArticleDefectPhoto.id')

class ArticleDefectPhoto(db.Model):
    __tablename__='article_defect_photos'
    id=db.Column(db.Integer,primary_key=True)
    defect_id=db.Column(db.Integer,db.ForeignKey('article_defects.id'),nullable=False,index=True)
    filename=db.Column(db.String(80),unique=True,nullable=False)

class InspectionResetRun(db.Model):
    __tablename__='inspection_reset_runs'
    id=db.Column(db.String(100),primary_key=True)
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    backup=db.Column(db.String(500),nullable=False)
    counts=db.Column(db.JSON,nullable=False)
