"""Personal project work and tool repair evidence, independent of machine times."""
from datetime import datetime
from sqlalchemy import text
from factoryos.extensions import db

class Workspace(db.Model):
    __tablename__='project_workspaces'
    order_id=db.Column(db.Integer,db.ForeignKey('orders.id'),primary_key=True)
    version=db.Column(db.Integer,nullable=False,default=1)

class Member(db.Model):
    __tablename__='project_members'
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    user=db.relationship('User')

class Task(db.Model):
    __tablename__='project_tasks'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    title=db.Column(db.String(200),nullable=False)
    assignee_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    due_date=db.Column(db.Date)
    status=db.Column(db.String(30),nullable=False,default='open')
    assignee=db.relationship('User')

class Link(db.Model):
    __tablename__='project_links'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    sampling_id=db.Column(db.Integer,db.ForeignKey('sampling_orders.id'))
    error_id=db.Column(db.Integer,db.ForeignKey('tool_errors.id'))
    sampling=db.relationship('SamplingOrder')
    error=db.relationship('ToolError')
    __table_args__=(db.CheckConstraint('(sampling_id IS NOT NULL AND error_id IS NULL) OR (sampling_id IS NULL AND error_id IS NOT NULL)'),db.UniqueConstraint('project_id','sampling_id'),db.UniqueConstraint('project_id','error_id'))

class WorkTime(db.Model):
    __tablename__='project_work_times'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    started_at=db.Column(db.DateTime,nullable=False)
    ended_at=db.Column(db.DateTime)
    description=db.Column(db.String(500),nullable=False)
    link_id=db.Column(db.Integer,db.ForeignKey('project_links.id'))
    link=db.relationship('Link')
    cancelled=db.Column(db.Boolean,nullable=False,default=False)
    user=db.relationship('User')
    project=db.relationship('Order')
    __table_args__=(db.CheckConstraint('ended_at IS NULL OR ended_at > started_at'),db.Index('uq_project_running_user','user_id',unique=True,sqlite_where=text('ended_at IS NULL AND cancelled = 0')))

class Report(db.Model):
    __tablename__='project_reports'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    text=db.Column(db.Text,nullable=False)
    link_id=db.Column(db.Integer,db.ForeignKey('project_links.id'))
    link=db.relationship('Link')
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    user=db.relationship('User')
    photos=db.relationship('ReportPhoto',backref='report')

class ReportPhoto(db.Model):
    __tablename__='project_report_photos'
    id=db.Column(db.Integer,primary_key=True)
    report_id=db.Column(db.Integer,db.ForeignKey('project_reports.id'),nullable=False)
    filename=db.Column(db.String(50),nullable=False,unique=True)

class ToolPartEvent(db.Model):
    __tablename__='project_tool_part_events'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),nullable=False,index=True)
    tool_id=db.Column(db.Integer,db.ForeignKey('tools.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    operation=db.Column(db.String(20),nullable=False)
    part_name=db.Column(db.String(200),nullable=False)
    link_id=db.Column(db.Integer,db.ForeignKey('project_links.id'))
    link=db.relationship('Link')
    part_no=db.Column(db.String(100))
    serial_no=db.Column(db.String(100))
    position=db.Column(db.String(200),nullable=False)
    quantity=db.Column(db.Numeric(12,3),nullable=False)
    unit=db.Column(db.String(20),nullable=False)
    reason=db.Column(db.String(500),nullable=False)
    disposition=db.Column(db.String(200))
    occurred_at=db.Column(db.DateTime,nullable=False)
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    reverses_id=db.Column(db.Integer,db.ForeignKey('project_tool_part_events.id'),unique=True)
    tool=db.relationship('Tool')
    project=db.relationship('Order')
    user=db.relationship('User')
    __table_args__=(db.CheckConstraint('quantity > 0'),)

class Audit(db.Model):
    __tablename__='project_audits'
    id=db.Column(db.Integer,primary_key=True)
    project_id=db.Column(db.Integer,db.ForeignKey('orders.id'),index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    action=db.Column(db.String(100),nullable=False)
    data=db.Column(db.JSON,nullable=False)
    created_at=db.Column(db.DateTime,nullable=False,default=datetime.utcnow)
    user=db.relationship('User')

class WriteLock(db.Model):
    __tablename__='project_write_lock'
    id=db.Column(db.Integer,primary_key=True)
    revision=db.Column(db.Integer,nullable=False,default=0)

MODELS=(Workspace,Member,Task,Link,WorkTime,Report,ReportPhoto,ToolPartEvent,Audit,WriteLock)
