class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(db.String(200), nullable=True)
    company_address = db.Column(db.String(400), nullable=True)

    logo_filename = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
