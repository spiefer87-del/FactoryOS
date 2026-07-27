from datetime import datetime

from factoryos.extensions import db


class Machine(db.Model):
    __tablename__ = "machines"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =====================================================
    # IDENTIFIKATION
    # =====================================================

    machine_no = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    external_machine_no = db.Column(
        db.String(100)
    )

    name = db.Column(
        db.String(150)
    )

    description = db.Column(
        db.Text
    )

    machine_type = db.Column(
        db.String(50),
        nullable=False,
        default="injection_molding"
    )

    # =====================================================
    # HERSTELLER
    # =====================================================

    manufacturer = db.Column(
        db.String(150)
    )

    model = db.Column(
        db.String(150)
    )

    serial_no = db.Column(
        db.String(150)
    )

    build_year = db.Column(
        db.Integer
    )

    # =====================================================
    # STEUERUNG / AUTOMATION
    # =====================================================

    controller_type = db.Column(
        db.String(150)
    )

    automation_type = db.Column(
        db.String(150)
    )

    # =====================================================
    # BETRIEB / WARTUNG
    # =====================================================

    operating_hours = db.Column(
        db.Integer
    )

    last_service_at = db.Column(
        db.DateTime
    )

    next_service_at = db.Column(
        db.DateTime
    )

    # =====================================================
    # ORGANISATION
    # =====================================================

    location = db.Column(
        db.String(100)
    )

    machine_status = db.Column(
        db.String(50),
        nullable=False,
        default="aktiv"
    )

    # =====================================================
    # SYSTEM
    # =====================================================

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id")
    )

    created_by = db.relationship(
        "User"
    )

    # =====================================================
    # TYPABHÄNGIGE DATEN
    # =====================================================

    injection_molding_data = db.relationship(
        "InjectionMoldingData",
        back_populates="machine",
        uselist=False,
        cascade="all, delete-orphan"
    )


class InjectionMoldingData(db.Model):
    __tablename__ = "machine_injection_molding_data"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    machine_id = db.Column(
        db.Integer,
        db.ForeignKey("machines.id"),
        unique=True,
        nullable=False
    )

    # Schließeinheit
    clamping_force_kn = db.Column(db.Float)

    tie_bar_width_mm = db.Column(db.Float)
    tie_bar_height_mm = db.Column(db.Float)

    min_mold_height_mm = db.Column(db.Float)
    max_mold_height_mm = db.Column(db.Float)

    opening_stroke_mm = db.Column(db.Float)
    ejector_stroke_mm = db.Column(db.Float)

    max_tool_weight_kg = db.Column(db.Float)

    # Spritzeinheit
    screw_diameter_mm = db.Column(db.Float)
    max_shot_weight_g = db.Column(db.Float)
    max_injection_pressure_bar = db.Column(db.Float)

    heating_zones = db.Column(db.Integer)

    # Düse
    nozzle_radius_mm = db.Column(db.Float)
    nozzle_diameter_mm = db.Column(db.Float)

    machine = db.relationship(
        "Machine",
        back_populates="injection_molding_data"
    )
