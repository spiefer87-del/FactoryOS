"""Stable field locations for wizard validation; no submitted values in errors."""
from .schema import FIELDS, PROFILES, STEPS

CONTEXT_LABELS = {"machine_id":"Maschine", "article_id":"Artikel dieses Werkzeugs",
                  "material_id":"Hauptrohstoff", "masterbatch_id":"Farbbatch",
                  "context_confirmed":"Zuordnungen bestätigen"}


class ReportValidationError(ValueError):
    def __init__(self, message, *, field=None, profile=None, row=None, column=None, context=None):
        spec=FIELDS.get(field) or PROFILES.get(profile) or {}
        label=CONTEXT_LABELS.get(context) or spec.get("label","Einstellbericht")
        step=spec.get("step","identity")
        if profile and row is not None:
            label+=f" · Zeile {row+1}"
        if profile and column:
            columns={c[0]:c[1] for c in spec.get("columns",[])}
            label+=" · "+columns.get(column,{"label":"Stufe / Zone","active":"Aktiv","reason":"Begründung"}.get(column,column))
        elif field and column=="reason":
            label+=" · Begründung"
        self.errors=[dict(step=step,step_label=dict(STEPS).get(step,step),label=label,
                          message=message,field=field,profile=profile,row=row,column=column,context=context)]
        super().__init__(label+": "+message)


def error_payload(error):
    return dict(error=str(error),errors=error.errors) if isinstance(error,ReportValidationError) else dict(error=str(error))
