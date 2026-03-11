from extensions import db

from factoryos.modules.quality.models import (
    QualityInspectionPlanVersion,
    QualityInspectionSection,
    QualityInspectionCharacteristic,
    QualityInspectionGaugeCheck,
    QualityInspectionImage,
    QualityInspectionSnippet
)

from factoryos.modules.quality.inspection_plan.change_log_service import log_change

def create_new_revision(version_id, user_id):

    old_version = QualityInspectionPlanVersion.query.get_or_404(version_id)

    # neue Revisionsnummer
    new_revision = increment_revision(old_version.revision)

    new_version = QualityInspectionPlanVersion(
        plan_id=old_version.plan_id,
        revision=new_revision,
        status="draft"
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

        major, minor = revision.split(".")

        minor = int(minor) + 1

        return f"{major}.{minor}"

    except:

        return "1.1"
    
def copy_sections(old_version, new_version):

    for section in old_version.sections:

        new_section = QualityInspectionSection(

            version_id=new_version.id,
            title=section.title,
            section_type=section.section_type,
            drawing_path=section.drawing_path

        )

        db.session.add(new_section)
        db.session.flush()

        copy_characteristics(section, new_section)

        copy_gauge_checks(section, new_section)

        copy_images(section, new_section)

        copy_snippets(section, new_section)

def copy_characteristics(old_section, new_section):

    for c in old_section.characteristics:

        new_char = QualityInspectionCharacteristic(

            section_id=new_section.id,

            name=c.name,
            target_value=c.target_value,
            tolerance_minus=c.tolerance_minus,
            tolerance_plus=c.tolerance_plus,
            unit=c.unit,

            sort_order=c.sort_order,

            pos_x=c.pos_x,
            pos_y=c.pos_y

        )

        db.session.add(new_char)

def copy_gauge_checks(old_section, new_section):

    for g in old_section.gauge_checks:

        new_check = QualityInspectionGaugeCheck(

            section_id=new_section.id,

            name=g.name,
            gauge_id=g.gauge_id,
            method=g.method,

            sort_order=g.sort_order

        )

        db.session.add(new_check)

def copy_images(old_section, new_section):

    for img in old_section.images:

        new_img = QualityInspectionImage(

            section_id=new_section.id,

            image_path=img.image_path,
            description=img.description

        )

        db.session.add(new_img)

def copy_snippets(old_section, new_section):

    for snip in old_section.snippets:

        new_snip = QualityInspectionSnippet(

            section_id=new_section.id,

            image_path=snip.image_path,
            description=snip.description

        )

        db.session.add(new_snip)