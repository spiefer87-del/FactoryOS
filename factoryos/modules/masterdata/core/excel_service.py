import io
from openpyxl import Workbook


def export_to_excel(rows, columns):

    wb = Workbook()
    ws = wb.active

    ws.append(columns)

    for r in rows:

        line = []

        for c in columns:

            val = getattr(r, c, "")

            line.append(val)

        ws.append(line)

    output = io.BytesIO()

    wb.save(output)

    output.seek(0)

    return output