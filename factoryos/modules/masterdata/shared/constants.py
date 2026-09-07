TOOL_STATUSES = {
    "aktiv": "Aktiv",
    "wartung": "Wartung",
    "defekt": "Defekt",
    "external": "Beim Kunden",
    "scrapped": "Verschrottet"
}

TOOL_STATUS_COLORS = {
    "aktiv": "status-aktiv",
    "wartung": "status-wartung",
    "defekt": "status-defekt",
    "external": "status-external",
    "scrapped": "status-scrapped"
}

# =====================================================
# MASCHINEN
# =====================================================

MACHINE_TYPES = {
    "injection_molding": "Spritzgießmaschine",
    "milling": "Fräsmaschine",
    "lathe": "Drehmaschine",
    "assembly": "Montageanlage",
    "testing": "Prüfmaschine",
    "other": "Sonstige Maschine",
}


MACHINE_STATUSES = {
    "aktiv": "Aktiv",
    "wartung": "Wartung",
    "defekt": "Defekt",
    "stillgelegt": "Stillgelegt",
}


MACHINE_STATUS_COLORS = {
    "aktiv": "status-aktiv",
    "wartung": "status-wartung",
    "defekt": "status-defekt",
    "stillgelegt": "status-inaktiv",
}

# =====================================================
# MATERIALIEN
# =====================================================

MATERIAL_TYPES = {
    "plastic": "Kunststoffmaterial",
    "operating": "Betriebsstoff",
    "auxiliary": "Hilfsstoff",
}

MATERIAL_STATUSES = {
    "aktiv": "Aktiv",
    "gesperrt": "Gesperrt",
    "auslaufend": "Auslaufend",
    "inaktiv": "Inaktiv",
}

MATERIAL_STATUS_COLORS = {
    "aktiv": "status-aktiv",
    "gesperrt": "status-defekt",
    "auslaufend": "status-wartung",
    "inaktiv": "status-inaktiv",
}

POLYMER_TYPES = {
    "ABS": "ABS – Acrylnitril-Butadien-Styrol",
    "ASA": "ASA – Acrylnitril-Styrol-Acrylat",
    "EVA": "EVA – Ethylen-Vinylacetat",
    "PA6": "PA 6 – Polyamid 6",
    "PA66": "PA 6.6 – Polyamid 6.6",
    "PA11": "PA 11 – Polyamid 11",
    "PA12": "PA 12 – Polyamid 12",
    "PBT": "PBT – Polybutylenterephthalat",
    "PC": "PC – Polycarbonat",
    "PC_ABS": "PC/ABS – Polycarbonat/ABS-Blend",
    "PE_HD": "PE-HD – Polyethylen hoher Dichte",
    "PE_LD": "PE-LD – Polyethylen niedriger Dichte",
    "PEEK": "PEEK – Polyetheretherketon",
    "PET": "PET – Polyethylenterephthalat",
    "PMMA": "PMMA – Polymethylmethacrylat",
    "POM": "POM – Polyoxymethylen",
    "PP": "PP – Polypropylen",
    "PPS": "PPS – Polyphenylensulfid",
    "PS": "PS – Polystyrol",
    "SAN": "SAN – Styrol-Acrylnitril",
    "TPE": "TPE – Thermoplastisches Elastomer",
    "TPU": "TPU – Thermoplastisches Polyurethan",
    "PVC": "PVC – Polyvinylchlorid",
    "PUR": "PUR – Polyurethan",
    "OTHER": "Sonstiger Kunststoff",
}

MATERIAL_BASE_UNITS = {
    "kg": "kg",
    "g": "g",
    "l": "Liter",
    "ml": "ml",
    "st": "Stück",
    "m": "Meter",
    "m2": "Quadratmeter",
}

MATERIAL_DELIVERY_FORMS = {
    "granulate": "Granulat",
    "powder": "Pulver",
    "liquid": "Flüssig",
    "paste": "Paste",
    "solid": "Feststoff",
    "film": "Folie",
    "other": "Sonstige",
}
