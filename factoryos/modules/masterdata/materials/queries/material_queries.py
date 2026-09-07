from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from ..models import Material


def get_material(material_id):
    return (
        Material.query
        .options(joinedload(Material.created_by))
        .filter(Material.id == material_id)
        .first_or_404()
    )


def get_materials(search="", material_type="", status=""):
    query = Material.query

    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Material.material_no.ilike(term),
            Material.external_material_no.ilike(term),
            Material.name.ilike(term),
            Material.manufacturer.ilike(term),
            Material.color.ilike(term),
            Material.storage_location.ilike(term),
            Material.preferred_supplier_name.ilike(term),
            Material.description.ilike(term),
        ))

    if material_type:
        query = query.filter(Material.material_type == material_type)

    if status:
        query = query.filter(Material.material_status == status)

    return query.order_by(Material.material_no.asc()).all()
