from datetime import datetime

from factoryos.extensions import db


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    material_no = db.Column(db.String(100), unique=True, nullable=False)
    external_material_no = db.Column(db.String(100))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    material_type = db.Column(db.String(30), nullable=False, default="plastic")
    polymer_type = db.Column(db.String(30))
    manufacturer = db.Column(db.String(150))
    color = db.Column(db.String(100))
    color_no = db.Column(db.String(100))
    delivery_form = db.Column(db.String(50))
    base_unit = db.Column(db.String(20), nullable=False, default="kg")

    density_g_cm3 = db.Column(db.Float)
    melt_flow_rate = db.Column(db.String(100))
    drying_temperature_c = db.Column(db.Float)
    drying_time_h = db.Column(db.Float)
    processing_temperature_min_c = db.Column(db.Float)
    processing_temperature_max_c = db.Column(db.Float)
    mold_temperature_min_c = db.Column(db.Float)
    mold_temperature_max_c = db.Column(db.Float)

    storage_location = db.Column(db.String(150))
    minimum_stock = db.Column(db.Float)
    reorder_point = db.Column(db.Float)
    material_status = db.Column(db.String(30), nullable=False, default="aktiv")
    hazardous_material = db.Column(db.Boolean, nullable=False, default=False)

    # Wird beim späteren Lieferantenmodul mit dessen Datensatz verknüpft.
    # Absichtlich noch kein ForeignKey: Die Lieferantentabelle existiert heute nicht.
    supplier_id = db.Column(db.Integer, index=True)
    preferred_supplier_name = db.Column(db.String(200))
    supplier_material_no = db.Column(db.String(100))

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.relationship("User")
