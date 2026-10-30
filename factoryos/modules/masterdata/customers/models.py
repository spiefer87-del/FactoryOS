from factoryos.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    customer_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(150))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(80))
    street = db.Column(db.String(200))
    postal_code = db.Column(db.String(30))
    city = db.Column(db.String(120))
    country = db.Column(db.String(100))
    notes = db.Column(db.Text)
    active = db.Column(db.Boolean, nullable=False, default=True)

    articles = db.relationship("Article", back_populates="customer")

