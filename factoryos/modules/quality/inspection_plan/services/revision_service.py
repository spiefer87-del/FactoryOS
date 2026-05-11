from factoryos.extensions import db

from ..models import (
    QualityInspectionPlan,
    QualityInspectionPlanVersion,
    QualityInspectionSection,
    QualityInspectionCharacteristic,
    QualityInspectionIdentificationImage,
    QualityInspectionDimensionSnippet,
    QualityInspectionGaugeCheck
)

from factoryos.modules.quality.inspection_plan.services.change_log_service import log_change


def create_new_revision(version_id, user_id):

    old_version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    new_revision = increment_revision(old_version.revision)

    new_version = QualityInspectionPlanVersion(
        plan_id=old_version.plan_id,
        revision=new_revision,
        status="draft",
        is_dirty=True   # 🔥 wichtig
    )

    db.session.add(new_version)
    db.session.flush()

    copy_sections(old_version, new_version)

    log_change(
        new_version,
        "NEW_REVISION",
        f"Neue Revision {new_revision} aus Revision {old_version.revision} erzeugt",
        user_id
    )

    db.session.commit()

    return new_version


def increment_revision(revision):

    try:
        major, minor = str(revision).split(".")
        minor = int(minor) + 1
        return f"{major}.{minor}"
    except:
        return "1.1"


def copy_sections(old_version, new_version):

    for section in old_version.sections:

        new_section = QualityInspectionSection(
            plan_version_id=new_version.id,   # ✅ FIX
            title=section.title,
            section_type=section.section_type,
            drawing_path=section.drawing_path,
            sort_order=section.sort_order     # ✅ wichtig
        )

        db.session.add(new_section)
        db.session.flush()

        copy_characteristics(section, new_section)
        copy_gauge_checks(section, new_section)
        copy_images(section, new_section)
        copy_snippets(section, new_section)


def copy_characteristics(old_section, new_section):

    for c in old_section.characteristics:

        db.session.add(QualityInspectionCharacteristic(
            section_id=new_section.id,
            name=c.name,
            target_value=c.target_value,
            tolerance_minus=c.tolerance_minus,
            tolerance_plus=c.tolerance_plus,
            unit=c.unit,
            sort_order=c.sort_order,
            pos_x=c.pos_x,
            pos_y=c.pos_y,
            rotation=c.rotation
        ))


def copy_gauge_checks(old_section, new_section):

    for g in old_section.gauge_checks:

        db.session.add(QualityInspectionGaugeCheck(
            section_id=new_section.id,
            name=g.name,
            gauge_id=g.gauge_id,
            method=g.method,
            sort_order=g.sort_order
        ))


def copy_images(old_section, new_section):

    for img in old_section.images:

        db.session.add(QualityInspectionIdentificationImage(   # ✅ FIX
            section_id=new_section.id,
            image_path=img.image_path,
            description=img.description
        ))


def copy_snippets(old_section, new_section):

    for snip in old_section.snippets:

        db.session.add(QualityInspectionDimensionSnippet(   # ✅ FIX
            section_id=new_section.id,
            image_path=snip.image_path,
            description=snip.description,
            sort_order=snip.sort_order   # optional aber sauber
        ))
