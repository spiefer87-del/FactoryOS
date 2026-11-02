from sqlalchemy.orm import joinedload
from factoryos.modules.masterdata.machines.models import Machine
from .machine_excel_schema import machine_workbook


def export_machines_to_excel():
    machines = (Machine.query.options(joinedload(Machine.injection_molding_data))
                .order_by(Machine.machine_no.asc()).all())
    return machine_workbook(machines)
