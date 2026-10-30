REASONS = {
    "initial": "Erstbemusterung / Neuwerkzeug",
    "repair": "Nach Werkzeugreparatur",
    "tool_change": "Nach Werkzeugänderung",
    "article_change": "Nach Artikeländerung",
    "material_change": "Nach Werkstoffänderung",
    "color_change": "Nach Farbänderung",
    "other": "Sonstiges",
}
STATES = {"draft": "Entwurf", "in_progress": "In Bearbeitung", "review": "In Prüfung",
          "completed": "Erfolgreich abgeschlossen", "rework": "Nachbemusterung erforderlich"}
CHECKS = {
    "dimensions": "Maßprüfung / Prüfmaße eingehalten",
    "function": "Funktionsprüfung / Verbauprobe",
    "empb": "EMPB erstellt",
    "samples_sent": "Muster zum Kunden gesendet",
    "internal": "Interne Freigabe",
    "external": "Externe Kundenfreigabe",
    "setup_report": "Einstellbericht FB-18 erstellt / geändert",
    "inspection_plan": "Prüfanweisung erstellt / geändert",
    "packaging": "Verpackungsvorschrift erstellt / geändert",
    "work_instruction": "Arbeitsanweisung erstellt / geändert",
    "reference_sample": "Referenzmuster erstellt / geändert",
    "drawing": "Zeichnung geprüft",
    "obsolete": "Ungültige Dokumente eingezogen",
    "erp": "Stammdaten-Ordner und ERP aktualisiert",
}
CHECK_STATUSES = {"open": "Offen", "done": "Erledigt / erfüllt", "granted": "Freigabe erteilt",
                  "rejected": "Nicht erfüllt / abgelehnt", "not_required": "Nicht erforderlich"}
# Additional release gates for initial sampling, explicitly documented in the UI.
INITIAL_REQUIRED = ("dimensions", "function", "empb", "samples_sent", "drawing")
TEXT_FIELDS = {
    "other_reason": "Sonstiger Anlass / Erläuterung",
    "customer_order": "Kunden-Auftragsnummer",
    "color": "Farbe",
    "additives": "Zusätze / Anteil",
    "instructions": "Bemerkung / Vorgaben",
    "changes_result": "Änderungen und Ergebnis",
    "deviations": "Nicht erfüllte Anforderungen / Abweichungen",
    "operator": "Bemusterung durchgeführt von",
    "setter": "Einrichter",
    "packaging_proposal": "Verpackungsvorschlag",
    "delivery_note": "Lieferscheinnummer",
    "quality_note": "Bemerkung Qualitätswesen",
    "actions": "Weitere Maßnahmen",
    "cavity_result": "Kavitätenbezogene Ergebnisse (Erstbemusterung)",
    "initial_scope": "Prüfumfang / Anforderungen (Erstbemusterung)",
    "initial_evidence": "Prüfbericht- / EMPB-Referenz (Erstbemusterung)",
}
NUMBER_FIELDS = {
    "setup_minutes": ("Rüstzeit (Minuten)", False),
    "sampling_minutes": ("Musterungsdauer (Minuten)", False),
    "counter": ("Zählerstand", True),
    "cycle_seconds": ("Ist-Zykluszeit (Sekunden)", False),
    "cavities": ("Ist-Nester", True),
    "shot_weight": ("Schussgewicht (g)", False),
    "part_weight": ("Teilgewicht (g)", False),
    "runner_weight": ("Angussgewicht (g)", False),
}
DATE_FIELDS = {"planned_date": "Geplanter Musterungstermin", "sampled_date": "Bemustert am",
               "date_stamp_until": "Datumsanzeige bis"}
YES_NO_FIELDS = {"drawing_available": "Zeichnung liegt vor", "customer_material": "Material vom Kunden beigestellt",
                 "dry_material": "Material trocknen", "date_stamp": "Datumstempel vorhanden"}

