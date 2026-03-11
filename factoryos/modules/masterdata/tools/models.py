class ToolMasterdata(db.Model):
    __tablename__ = "tool_masterdata"

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

class ToolErrorReport(db.Model):
    __tablename__ = "tool_error_reports"

    id = db.Column(db.Integer, primary_key=True)

    # Werkzeugbezug (Stammdaten)
    tool_id = db.Column(db.Integer, db.ForeignKey("tool_masterdata.id"), nullable=False)

    # Wer hat gemeldet
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Inhalt
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    error_no = db.Column(db.String(20), unique=True, nullable=True)

    category = db.Column(db.String(50), nullable=True)  # z.B. Mechanik, Hydraulik ...
    priority = db.Column(db.String(20), nullable=True)  # niedrig/mittel/hoch
    status = db.Column(db.String(20), default="offen")  # offen/in_bearbeitung/erledigt

    # Bild
    image_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehungen
    tool = db.relationship("ToolMasterdata", foreign_keys=[tool_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

class ToolErrorImage(db.Model):
    __tablename__ = "tool_error_images"

    id = db.Column(db.Integer, primary_key=True)

    report_id = db.Column(db.Integer, db.ForeignKey("tool_error_reports.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    report = db.relationship("ToolErrorReport", backref="images")

class ToolErrorTitlePreset(db.Model):
    __tablename__ = "tool_error_title_presets"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)