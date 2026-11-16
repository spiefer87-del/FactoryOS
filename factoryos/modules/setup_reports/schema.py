"""FB-18 FP + hotrunner/cooling extensions, independent of controller layout."""
STEPS = [
    ("identity", "Werkzeug und Maschine"), ("injection", "Spritzparameter"),
    ("movement", "Werkzeug und Auswerfer"), ("temperature", "Temperaturen"),
    ("material", "Material und Farbe"), ("additional", "Weitere Angaben"),
    ("review", "Prüfen und abschließen"),
]
FIELDS = {}


def fields(step, definitions):
    for key, label, unit in definitions:
        FIELDS[key] = dict(key=key, label=label, unit=unit, step=step,
                           kind="number" if unit else "text")


fields("identity", [
    ("tool_no", "Werkzeugnummer", ""), ("tool_name", "Werkzeugbezeichnung", ""),
    ("machine_no", "Maschinennummer", ""), ("machine_name", "Maschinentyp / Bezeichnung", ""),
    ("controller", "Steuerung", ""), ("article_no", "Artikelnummer", ""),
    ("article_name", "Artikelbezeichnung", ""), ("customer", "Kunde", ""),
    ("drawing_no", "Zeichnungsnummer", ""), ("drawing_revision", "Zeichnungsindex", ""),
    ("cavities", "Fachzahl / aktive Kavitäten", "Stück"),
    ("screw_diameter", "Schneckendurchmesser", "mm"),
    ("nozzle_radius", "Düsenradius", "mm"), ("tool_location", "Werkzeug-Lagerort", ""),
])
fields("injection", [
    ("cycle_target", "Soll-Zykluszeit", "s"), ("injection_time", "Spritzzeit (gemessen)", "s"),
    ("cooling_time", "Restkühlzeit (Einstellung)", "s"), ("pause_time", "Pausenzeit", "s"),
    ("dosing_time", "Dosierzeit (gemessen)", "s"), ("dosing_delay", "Dosierverzögerung", "s"),
    ("unit_return_delay", "Spritzeinheit zurück verzögert", "s"),
    ("injection_pressure", "Spritzdruck (Einstellung)", "bar_spez"),
    ("peak_pressure", "Spitzenwert pmax (gemessen)", "bar_spez"),
    ("switch_pressure", "Umschaltdruck (gemessen)", "bar_spez"),
    ("back_pressure", "Staudruck", "bar_spez"),
    ("dosing_position", "Plastifizierweg / Dosierposition", "cm³"),
    ("decompression", "Dekompressions-Endposition", "cm³"),
    ("decompression_speed", "Dekompressionsgeschwindigkeit", "cm³/s"),
    ("switch_position", "Umschaltposition", "cm³"),
    ("switch_criterion", "Aktives Umschaltkriterium", ""),
    ("cushion", "Massepolster (gemessen)", "cm³"),
    ("screw_speed", "Schnecken-Drehzahl / Umfangsgeschwindigkeit", "mm/s"),
    ("holding_speed", "Nachdruckgeschwindigkeit", "cm³/s"),
])
fields("movement", [
    ("clamping_force", "Schließkraft (Einstellung)", "kN"),
    ("open_position", "Werkzeug-Offenposition", "mm"),
    ("mold_height", "Werkzeug-Einbauhöhe", "mm"),
    ("mold_protection_force", "Werkzeugschutz-Kraft", "kN"),
    ("mold_protection_time", "Werkzeugschutz-Zeit", "s"),
    ("ejector_strokes", "Auswerferhübe", "Stück"),
    ("core_sequence", "Kernzugablauf / Endschalter", ""),
    ("mold_safety", "Werkzeug-/Auswerfer-Sicherheitshinweise", ""),
])
fields("temperature", [
    ("nozzle_cooling", "Werkzeugtemperierung Düsenseite", "°C"),
    ("ejector_cooling", "Werkzeugtemperierung Auswerferseite", "°C"),
    ("core_cooling", "Werkzeugtemperierung Kerne", "°C"),
    ("slide_cooling", "Werkzeugtemperierung Schieber", "°C"),
    ("temperature_devices", "Anzahl Temperiergeräte", "Stück"),
    ("hotrunner_controller", "Heißkanal-Regelgerät / Nummer", ""),
])
fields("material", [
    ("material_no", "Rohstoffnummer", ""), ("material_name", "Rohstoff / Handelsname", ""),
    ("manufacturer", "Rohstoffhersteller", ""), ("polymer", "Werkstoffgruppe", ""),
    ("color", "Rohstofffarbe / Farbnummer", ""),
    ("batch_no", "Farbbatch-Nummer", ""), ("batch_name", "Farbbatch-Bezeichnung", ""),
    ("batch_percent", "Farbbatch-Zugabe bezogen auf Hauptrohstoff", "%"),
    ("batch_color", "Gewünschter Farbton / RAL", ""),
    ("drying_temperature", "Verwendete Trocknungstemperatur", "°C"),
    ("drying_time", "Verwendete Trocknungszeit", "h"),
    ("shot_weight", "Schussgewicht inkl. Anguss", "g"),
    ("part_weight", "Teilegewicht / Gewichte je Kavität", ""),
    ("shot_without_runner", "Schussgewicht ohne Anguss", "g"),
    ("runner_weight", "Angussgewicht", "g"),
    ("material_consumption", "Materialverbrauch", "kg/h"), ("gate_system", "Angusssystem", ""),
])
fields("additional", [
    ("mode", "Betriebsart (Halb-/Vollautomat)", ""),
    ("nozzle_return", "Düse abfahren (ja/nein)", ""),
    ("sampling_no", "Musterungsnummer / Auftragsbezug", ""),
    ("handling", "Entnahmegerät / Roboter", ""), ("robot_head", "Roboterkopf-Nummer", ""),
    ("packaging", "Verpackung", ""), ("notes", "Bemerkungen / Arbeitsablauf", ""),
    ("record_date", "Einstelldatum (JJJJ-MM-TT)", ""), ("operator", "Einrichter / Name", ""),
])

PROFILES = {
    "injection_profile": dict(label="Einspritzprofil", step="injection", columns=[("position", "Weg / Position", "cm³"), ("speed", "Geschwindigkeit", "cm³/s")]),
    "holding_profile": dict(label="Nachdruckprofil", step="injection", columns=[("pressure", "Druck", "bar_spez"), ("time", "Zeit", "s")]),
    "closing_profile": dict(label="Werkzeug schließen", step="movement", columns=[("position", "Position", "mm"), ("speed", "Geschwindigkeit", "mm/s"), ("force", "Kraft", "kN"), ("time", "Zeit", "s")]),
    "opening_profile": dict(label="Werkzeug öffnen", step="movement", columns=[("position", "Position", "mm"), ("speed", "Geschwindigkeit", "mm/s"), ("time", "Zeit", "s")]),
    "ejector_forward": dict(label="Auswerfer vor", step="movement", columns=[("position", "Position", "mm"), ("speed", "Geschwindigkeit", "mm/s"), ("pressure", "Druck", "bar"), ("time", "Zeit", "s")]),
    "ejector_back": dict(label="Auswerfer zurück", step="movement", columns=[("position", "Position", "mm"), ("speed", "Geschwindigkeit", "mm/s"), ("pressure", "Druck", "bar"), ("time", "Zeit", "s")]),
    "cylinder": dict(label="Zylindertemperaturen (Soll und Ist getrennt)", step="temperature", columns=[("set", "Soll", "°C"), ("actual", "Ist", "°C"), ("plus", "Toleranz +", "°C"), ("minus", "Toleranz -", "°C")]),
    "hotrunner": dict(label="Heißkanal-Zonen", step="temperature", columns=[("set", "Soll", "°C"), ("actual", "Ist", "°C")]),
    "cooling": dict(label="Kühlanschlussplan", step="temperature", columns=[("connection", "Anschluss / Kreislauf", ""), ("device", "Temperiergerät", ""), ("set", "Soll", "°C")]),
    "cores": dict(label="Kernzüge / Pneumatik", step="movement", columns=[("sequence", "Ablauf / Freigabe", ""), ("position", "Position", "mm"), ("pressure", "Druck", "bar"), ("time", "Zeit", "s")]),
}
UNITS = {"bar_spez": ["bar_spez", "bar"], "cm³": ["cm³", "mm"],
         "cm³/s": ["cm³/s", "mm/s"], "mm/s": ["mm/s", "U/min"]}
CYLINDER_ZONE_LABELS = ("DH", "MH 3", "MH 2", "MH 1", "Einzug")


def profile_defaults():
    """Fresh structures only: no process temperatures/tolerances are guessed."""
    return {"cylinder": dict(rows=[dict(label=label, active="yes", values={
        key:dict(value="",unit=unit) for key,_,unit in PROFILES["cylinder"]["columns"]
    }) for label in CYLINDER_ZONE_LABELS], status="open", reason="", origin="manual", photo_id=None)}


ORIGINS = {"manual": "Handeingabe", "master": "Stammdatenvorschlag", "recommendation": "Materialvorgabe - Verwendung bestätigen", "photo": "Foto-Vorschlag", "previous": "Früherer Bericht - erneut prüfen"}
PERMISSIONS = {
    "view": "Einstellberichte, Historie und zugehörige Fotos am Werkzeug ansehen.",
    "create": "Einstellberichte am Werkzeug anlegen und frühere Berichte als ungeprüfte Vorlage verwenden.",
    "edit": "Offene Einstellberichte manuell bearbeiten, Stammdatenvorschläge prüfen und Maschinenfotos lokal auslesen.",
    "release": "Vollständig geprüfte Einstellberichte abschließen. Keine Maschinen- oder Sicherheitsfreigabe.",
    "pdf_export": "Einstellberichte als PDF herunterladen und ausdrucken.",
    "external_ocr": "Maschinenfotos nach ausdrücklicher Bestätigung extern mit Groq auslesen. Benötigt zusätzlich Bearbeitungsrecht.",
}
