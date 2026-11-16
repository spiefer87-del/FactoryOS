"""One catalog for editor, validation, revisions and PDF."""
MODULES = {
    'identification': ('Identifizierung', '🆔', 'Artikel, Kennzeichnung, Nest und Referenzbilder zuordnen.'),
    'dimension': ('Maßprüfung', '📏', 'Zeichnung, Prüfmaße und Toleranzen.'),
    'gauge': ('Lehrenprüfung', '🧪', 'Messmittel aus dem Prüfmittelstamm und Prüfmethode.'),
    'visual': ('Sichtprüfung', '👁', 'Oberfläche, Grat, Einfallstellen und Vergleichsmuster.'),
    'text': ('Textprüfung / Hinweise', '📝', 'Beschriftungen, Dokumente und besondere Prüfanweisungen.'),
    'weight': ('Gewichtsprüfung', '⚖', 'Teilegewicht mit Sollwert, Toleranzen und Einheit.'),
    'function': ('Funktionsprüfung', '⚙', 'Montage, Passung, Bewegung und Funktionskriterien.'),
    'material': ('Material und Farbe', '🎨', 'Werkstoff, Farbton, Charge und Freigabemuster prüfen.'),
    'packaging': ('Verpackung und Kennzeichnung', '📦', 'Verpackung, Etikett, Menge und Rückverfolgbarkeit.'),
}
STATUS_LABELS = {'draft': 'Entwurf', 'review': 'In Prüfung', 'released': 'Freigegeben', 'closed': 'Geschlossen'}
