from factoryos.extensions import db
from factoryos.modules.masterdata.materials.models import Material
from factoryos.modules.masterdata.customers.models import Customer
from factoryos.modules.masterdata.shared.models.article_tool import article_tools


class Article(db.Model):

    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)

    article_no = db.Column(db.String(50), unique=True, nullable=False)

    article_name = db.Column(db.String(200), nullable=False)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    customer = db.relationship("Customer", back_populates="articles")

    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=True, index=True)
    material = db.relationship("Material", foreign_keys=[material_id])

    description = db.Column(db.Text)

    status = db.Column(db.String(20), default="active")

    shot_weight_g = db.Column(db.Float)
    cycle_time_s = db.Column(db.Float)
    pack_unit = db.Column(db.Integer)
    drawing_no = db.Column(db.String(100))
    drawing_revision = db.Column(db.String(20))
    masterbatch_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=True, index=True)
    masterbatch = db.relationship("Material", foreign_keys=[masterbatch_id])
    masterbatch_percent = db.Column(db.Float, nullable=True)


    tools = db.relationship(
        "Tool",
        secondary=article_tools,
        back_populates="articles"
    )
