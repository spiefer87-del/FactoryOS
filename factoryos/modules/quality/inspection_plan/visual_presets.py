"""Editable wording aids, not product-specific tolerances or approvals."""
VISUAL_PRESETS = [
    ('grat','Grat / Schwimmhaut','Kein unzulässiger Grat an Trennlinien, Kanten und Durchbrüchen.'),
    ('luftschlieren','Luftschlieren','Keine unzulässigen Luftschlieren auf den festgelegten Prüfflächen.'),
    ('brenner','Brenner / Brandstellen','Keine unzulässigen Brandstellen oder verbrannten Bereiche.'),
    ('dieseleffekt','Dieseleffekt','Keine unzulässigen dunklen Verfärbungen oder Brandstellen in den festgelegten Prüfbereichen.'),
    ('einfallstellen','Einfallstellen','Keine unzulässigen Einfallstellen auf den festgelegten Prüfflächen.'),
    ('bindenaehte','Bindenähte','Lage und Ausprägung der Bindenähte entsprechen der freigegebenen Vorgabe.'),
    ('silberschlieren','Silberschlieren','Keine unzulässigen silbrigen Schlieren auf den festgelegten Prüfflächen.'),
    ('fuellung','Unvollständige Füllung','Alle vorgesehenen Konturen, Rippen und Durchbrüche sind vollständig ausgebildet.'),
    ('punkte','Schwarze Punkte / Fremdpartikel','Keine unzulässigen schwarzen Punkte oder sichtbaren Fremdpartikel.'),
    ('farbe','Farbabweichungen / Farbschlieren','Farbton und Farbverteilung entsprechen der freigegebenen Referenz.'),
    ('fliesslinien','Fließlinien','Keine unzulässigen Fließlinien auf den festgelegten Prüfflächen.'),
    ('verzug','Verzug / Verformung','Keine unzulässigen sichtbaren Verformungen gegenüber der freigegebenen Vorgabe.'),
    ('risse','Risse / Spannungsrisse','Keine sichtbaren unzulässigen Risse in den festgelegten Prüfbereichen.'),
    ('oberflaeche','Kratzer / Druckstellen','Keine unzulässigen Kratzer, Druckstellen oder Oberflächenbeschädigungen.'),
]


def visual_presets():
    return [dict(key=key,name=name,requirement=criterion+' Zulässige Ausprägung, Prüfflächen und Grenzmuster/Zeichnungsbezug vor Freigabe konkret festlegen.',
                 method='Sichtvergleich mit freigegebenem Grenzmuster / Zeichnung; Prüfbedingungen festlegen.')
            for key,name,criterion in VISUAL_PRESETS]
