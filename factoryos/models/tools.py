from datetime import datetime
from factoryos.extensions import db

class Tool(db.Model):
    __tablename__ = "tools"

    id = db.Column(db.Integer, primary_key=True)

    # WKZ-Nr = eindeutig
    tool_no = db.Column(db.String(100), unique=True, nullable=False, index=True)

    article_no = db.Column(db.String(100), nullable=True, index=True)
    article_name = db.Column(db.String(255), nullable=True, index=True)
    shot_weight_g = db.Column(db.Float, nullable=True)   # Schussgewicht in Gramm
    cycle_time_s = db.Column(db.Float, nullable=True)    # Zykluszeit in Sekunden


    cavities = db.Column(db.Integer, nullable=True)     # Formnester
    pack_unit = db.Column(db.Integer, nullable=True)    # VP Einheit

    location = db.Column(db.String(100), nullable=True, index=True)

    # manuell pflegbar
    tool_status = db.Column(db.String(50), nullable=False, default="OK")



