"""German UI text only. Internal permission identifiers and grants are untouched."""
GROUP_LABELS = {
    "activity": "Aktivitätsprotokoll", "articles": "Artikel", "customers": "Kunden",
    "machines": "Maschinen", "materials": "Materialien und Farbbatches",
    "orders": "Aufträge", "production": "Produktion und Maschinenbuchung",
    "projects": "Projekte", "quality": "Qualitätssicherung",
    "sampling": "Musterungsaufträge", "tool_error": "Werkzeugfehlermeldungen",
    "tools": "Werkzeuge", "users": "Benutzerverwaltung",
}
ROLE_LABELS = {"admin": "Systemadministration", "production": "Produktion",
               "quality": "Qualitätssicherung", "qm": "Qualitätsmanagement",
               "schichtleiter": "Schichtleitung"}
ACTION_ORDER = ("view", "create", "edit", "documents", "start", "stop", "setup", "events",
                "inspect", "submit_review", "return_to_draft", "release", "close", "revision",
                "excel_import", "excel_export", "pdf_export", "delete")
PERMISSION_TEXT = {}


def add(group, action, title, description):
    PERMISSION_TEXT[group + "." + action] = {"title": title, "description": description}


for group, noun in (("articles", "Artikel"), ("customers", "Kunden"),
                    ("machines", "Maschinen"), ("materials", "Materialien"),
                    ("orders", "Aufträge"), ("tools", "Werkzeuge")):
    add(group, "view", "Ansehen", f"Übersicht und Detailseiten für {noun} öffnen und gespeicherte Angaben lesen.")
    add(group, "create", "Anlegen", f"Neue {noun} erfassen und speichern.")
    add(group, "edit", "Bearbeiten", f"Angaben bestehender Datensätze im Bereich {GROUP_LABELS[group]} ändern.")
    add(group, "delete", "Löschen", f"{noun} löschen, soweit bestehende Zuordnungen und fachliche Sperren dies zulassen.")

for group in ("machines", "materials", "tools", "tool_error"):
    add(group, "excel_import", "Excel importieren", "Datensätze aus einer Excel-Datei anlegen oder aktualisieren und die Importvorlage herunterladen.")
    add(group, "excel_export", "Excel exportieren", "Die Datensätze dieses Bereichs als Excel-Datei herunterladen.")

for group in ("materials", "tools"):
    add(group, "documents", "Dokumente verwalten", "Dateien und Bilder hochladen sowie vorhandene Dokumente ins Archiv verschieben. Zum Herunterladen wird das Leserecht benötigt.")

add("activity", "view", "Protokoll ansehen", "Das zentrale Aktivitätsprotokoll mit protokollierten Änderungen und Benutzeraktionen öffnen.")
add("orders", "delete", "Löschen", "Gewöhnliche Aufträge löschen. Musterungsaufträge werden nicht über diese Funktion gelöscht.")
add("tools", "edit", "Bearbeiten", "Werkzeugdaten ändern und das Hauptbild eines Werkzeugs festlegen.")
add("production", "view", "Übersicht ansehen", "Die Produktionsübersicht und die Maschinen-Timeline öffnen.")
add("production", "start", "Buchungen starten", "Aufträge und Projektzeiten starten sowie pausierte oder unterbrochene Buchungen fortsetzen.")
add("production", "stop", "Buchungen stoppen", "Buchungen beenden, Maschinenstillstände erfassen und laufende Musterungsbuchungen stoppen.")
add("production", "setup", "Rüstvorgänge erfassen", "Rüstvorgänge an Maschinen starten und dem vorgesehenen Auftrag oder Werkzeug zuordnen. Die Arbeitszeiten im Produktionskalender werden dadurch nicht geändert.")
add("production", "events", "Maschinenereignisse erfassen", "Ereignisse an einer Maschine mit ergänzenden Angaben oder Kommentaren erfassen.")
add("projects", "view", "Projekte ansehen", "Die Projektübersicht öffnen und vorhandene Projekte ansehen.")
add("projects", "create", "Projekte anlegen", "Neue Projektaufträge anlegen. Zusätzlich ist die Rolle Schichtleitung oder Systemadministration erforderlich. Für Zeitbuchungen gelten die Start- und Stopprechte der Produktion.")
add("quality", "view", "Qualitätsdaten ansehen", "Qualitätsübersichten, Prüfpläne und Prüfmittel mit ihren Details aufrufen.")
add("quality", "inspect", "Prüfungen und Prüfunterlagen bearbeiten", "Prüfpläne und Prüfmittel anlegen oder bearbeiten, Prüfmerkmale pflegen sowie Kalibrierungen und Prüfmittelstatus erfassen.")
add("quality", "delete", "Prüfunterlagen löschen", "Prüfpläne und zugehörige Abschnitte, Markierungen oder hochgeladene Prüfunterlagen löschen, soweit die Anwendung dies zulässt.")
add("quality", "pdf_export", "Prüfunterlagen exportieren", "Prüfpläne als PDF und zugehörige Zeichnungsausschnitte herunterladen.")
add("sampling", "view", "Musterungen ansehen", "Die Musterungsübersicht und die Detailseiten vorhandener Musterungsaufträge aufrufen.")
add("sampling", "create", "Musterungsaufträge anlegen", "Neue Musterungsaufträge oder Nachbemusterungen mit genau einem Musterungsanlass erstellen.")
add("sampling", "edit", "Musterungen bearbeiten", "Offene Musterungsaufträge, Durchführung, Ergebnisse und Prüfangaben bearbeiten. Abgeschlossene Aufträge bleiben schreibgeschützt.")
add("sampling", "release", "Abschließen und Freigaben pflegen", "Den erfolgreichen Abschluss einer Musterung auslösen und Kundenfreigaben nachverfolgen. Alle fachlichen Abschlussprüfungen und die besonderen Regeln zur Erstbemusterung gelten weiterhin.")
add("sampling", "pdf_export", "PDF und Druckansicht öffnen", "Musterungsaufträge als PDF herunterladen oder in der Druckansicht öffnen.")
add("tool_error", "view", "Fehlermeldungen ansehen", "Werkzeugfehlermeldungen mit ihren Details und gespeicherten Bildern ansehen.")
add("tool_error", "create", "Fehlermeldungen anlegen", "Neue Werkzeugfehlermeldungen erfassen und als Entwurf speichern.")
add("tool_error", "edit", "Entwürfe bearbeiten", "Bearbeitbare Werkzeugfehlermeldungen, temporäre Bilder und Bildmarkierungen ändern. Die Bearbeitungssperren des jeweiligen Status bleiben bestehen.")
add("tool_error", "delete", "Fehlermeldungen löschen", "Werkzeugfehlermeldungen löschen, soweit die fachlichen Regeln dies zulassen.")
add("tool_error", "submit_review", "Zur Prüfung einreichen", "Einen bearbeiteten Entwurf zur Prüfung weitergeben.")
add("tool_error", "return_to_draft", "Zur Bearbeitung zurückgeben", "Eine Fehlermeldung zur erneuten Bearbeitung in den Entwurfsstatus zurücksetzen.")
add("tool_error", "release", "Fehlermeldungen freigeben", "Geprüfte Werkzeugfehlermeldungen freigeben. Vorgeschriebene Statusübergänge bleiben bestehen.")
add("tool_error", "close", "Fehlermeldungen abschließen", "Eine Werkzeugfehlermeldung abschließen, wenn die fachlichen Voraussetzungen erfüllt sind.")
add("tool_error", "revision", "Neue Revision anlegen", "Eine weitere Revision einer bestehenden Werkzeugfehlermeldung erstellen.")
add("tool_error", "pdf_export", "PDF herunterladen", "Eine Werkzeugfehlermeldung mit den vorgesehenen Angaben als PDF herunterladen.")
add("users", "view", "Benutzer ansehen", "Die Benutzerübersicht mit Namen, zugeordneter Rolle und Aktivstatus öffnen.")
add("users", "create", "Benutzer anlegen", "Neue Benutzerkonten mit einer zulässigen Rolle anlegen. Nichtadministrative Nutzer dürfen keine weitergehenden Rollenrechte vergeben.")
add("users", "edit", "Benutzer bearbeiten", "Zulässige Benutzerkonten umbenennen, umstufen, aktivieren oder deaktivieren und deren Passwort zurücksetzen. Höher privilegierte Konten bleiben geschützt; das eigene Passwort wird im Profil geändert.")
add("users", "delete", "Benutzer löschen", "Unbenutzte Konten im zulässigen Verwaltungsbereich löschen. Konten mit zugeordneten Vorgängen stattdessen deaktivieren; das eigene Konto bleibt geschützt.")


def group_label(name):
    return GROUP_LABELS.get(name, "Weitere Berechtigungen")


def role_label(role):
    name = role.name or ""
    return ROLE_LABELS.get(name.strip().casefold(), name or "Unbenannte Rolle")


def permission_text(permission):
    if permission.name in PERMISSION_TEXT:
        return PERMISSION_TEXT[permission.name]
    description = (permission.description or "").strip()
    # Do not present raw identifiers as a supposedly helpful description.
    if not description or description == permission.name or (" " not in description and "." in description):
        description = "Für dieses zusätzliche Recht ist noch keine fachliche Beschreibung hinterlegt. Die technische Kennung kann zur Zuordnung eingeblendet werden."
    return {"title": "Zusätzliches Recht", "description": description}


def permission_sort_key(permission):
    action = permission.name.split(".", 1)[-1]
    rank = ACTION_ORDER.index(action) if action in ACTION_ORDER else len(ACTION_ORDER)
    return rank, permission_text(permission)["title"], permission.name
