"""German UI text only. Internal permission identifiers and grants are untouched."""
GROUP_LABELS = {
    'defects':'Artikel-Fehlerkatalog','complaints':'Reklamationen',
    'inventory':'Lagerverwaltung',
    "activity": "Aktivitätsprotokoll", "articles": "Artikel", "customers": "Kunden",
    "machines": "Maschinen", "materials": "Materialien und Farbbatches",
    "orders": "Aufträge", "production": "Produktion und Maschinenbuchung",
    "projects": "Projekte", "quality": "Qualitätssicherung",
    "sampling": "Musterungsaufträge", "tool_error": "Werkzeugfehlermeldungen",
    "tools": "Werkzeuge", "users": "Benutzerverwaltung",
    "setup_reports": "Werkzeug-Einstellberichte",
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

for action,title in [('view','Fehlerkatalog und Fotos ansehen'),('create','Artikelfehler mit Fotos erfassen'),('edit','Artikelfehler bearbeiten / archivieren')]:
    add('defects',action,title,title+'; keine Werkzeugfehlermeldung oder Maschinenfreigabe.')
add('complaints','view','Reklamationen ansehen','Vorbereiteten Reklamationsbereich öffnen.')
add('defects','delete_photos','Gespeicherte Fehlerfotos löschen','Einzelne Fotos aus dem Artikel-Fehlerkatalog entfernen; keine Löschung des Fehlereintrags.')
add('defects','pdf_export','Fehlerkatalog als PDF drucken','Einzelne Fehlereinträge oder den Artikel-Fehlerkatalog mit Fotos als PDF exportieren.')
add('defects','delete','Fehlereinträge vollständig löschen','Einen vollständigen Fehlereintrag einschließlich Fotos nach Bestätigung löschen; Löschgrund und Originaldaten werden protokolliert.')

for action,title in [('view','Lager ansehen'),('locations','Lagerplätze anlegen'),('production','Produktionsübergaben bestätigen'),('receive','Lagerannahme / Übergabeausschuss'),('release','Bestände sperren / freigeben'),('adjust','Erstbestände / Gegenbuchungen'),('move','Lagerbestände umlagern'),('scrap','Lagerausschuss buchen'),('dispatch','Reservieren, kommissionieren, versenden und zurücknehmen')]:
    add('inventory',action,title,title+'; bestätigte Mengen und nachvollziehbare Belege erforderlich.')


add('orders','complete','Aufträge im Büro abschließen','Fertigungsaufträge auch ohne laufende Maschine mit bestätigten Endmengen abschließen. Keine Musterungsfreigabe und kein Wiederöffnen.')
add('production','complete_order','Aufträge an der Maschine abschließen','Den aktuell zugeordneten Fertigungsauftrag mit Endmengen abschließen und die Produktion ausbuchen. Störungen/Wartungen werden nicht automatisch quittiert.')
add('production','cancel_booking','Falsche Zeitbuchungen stornieren','Abgeschlossene, nicht fachlich gebundene Zeitbuchungen mit Vorschau und Begründung aus der Zeitwertung nehmen. Keine Löschung von Mengen, Rüstnachweisen oder Aufträgen.')
add('production','edit_setup_time','Rüst- und Abrüstzeiten korrigieren','Abgeschlossene einfache Rüst-/Abrüstbuchungen und zugehörige Zeitnachweise mit Vorschau und Begründung korrigieren. Werkzeugbestand bleibt unverändert.')
add('production','confirm_deviation','Laufzeitabweichungen begründen','Soll-/Laufzeitabweichungen am Auftrag mit Ursache und Maßnahmen bestätigen. Keine Änderung der Maschinenparameter oder bestätigten Mengen.')
add('production','delete_booking','Zeitbuchungen vollständig löschen','Abgeschlossene Zeitbuchungen und gegebenenfalls den eindeutig zugehörigen einfachen Rüstnachweis nach Prüfung vollständig löschen. Originaldaten werden protokolliert. Keine Löschung von Aufträgen oder Mengen.')


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
add("orders", "excel_import", "ERP-Aufträge importieren", "ERP-Exceldateien prüfen und eigene Importentwürfe bearbeiten. Aufträge und fehlende Stammdaten erst nach Bestätigung mit den jeweils zusätzlich erforderlichen Anlage- oder Bearbeitungsrechten übernehmen.")
add("tools", "edit", "Bearbeiten", "Werkzeugdaten ändern und das Hauptbild eines Werkzeugs festlegen.")
add("production", "view", "Übersicht ansehen", "Die Produktionsübersicht und die Maschinen-Timeline öffnen.")
add("production", "start", "Buchungen starten", "Aufträge und Projektzeiten starten sowie pausierte oder unterbrochene Buchungen fortsetzen.")
add("production", "stop", "Buchungen stoppen", "Buchungen beenden, Maschinenstillstände erfassen und laufende Musterungsbuchungen stoppen.")
add("production", "edit_booking_time", "Start- und Endzeiten korrigieren", "Tatsächliche Start- und Endzeiten von Produktions- und offenen Musterungsbuchungen mit Vorschau und Begründung korrigieren. Überschneidungen bleiben gesperrt; jede Änderung wird protokolliert.")
add("production", "setup", "Rüstvorgänge erfassen", "Rüstvorgänge an Maschinen starten und dem vorgesehenen Auftrag oder Werkzeug zuordnen. Die Arbeitszeiten im Produktionskalender werden dadurch nicht geändert.")
add("production", "events", "Maschinenereignisse erfassen", "Ereignisse an einer Maschine mit ergänzenden Angaben oder Kommentaren erfassen.")
add("production", "clear_fault", "Maschine entstören", "Die Behebung einer Maschinenstörung mit Begründung bestätigen. Produktion wird dadurch nicht automatisch wieder gestartet.")
add("production", "maintenance", "Wartung buchen", "Wartung an einer Maschine mit Beschreibung starten und beenden. Es wird kein Wartungsintervall in den Stammdaten verändert.")
add("production", "plan", "Aufträge planen", "Auftragsreihenfolgen je Maschine, Rüstzeiten und begründete Verfügbarkeitsannahmen pflegen. Planung startet keine Maschine automatisch.")
add("projects", "view", "Projekte ansehen", "Die Projektübersicht öffnen und vorhandene Projekte ansehen.")
add("projects", "create", "Projekte anlegen", "Eigene Projektaufträge mit optionaler Werkzeugzuordnung anlegen. Zusätzlich wird das Projektesichtrecht benötigt.")
add('projects','view_all','Alle Projekte überblicken','Auch fremde Projekte, Arbeitsberichte und Zeitnachweise lesen. Keine automatische Bearbeitungserlaubnis.')
add('projects','work','In eigenen Projekten arbeiten','Als Projektmitglied Zeiten, Berichte, Vorgangsverknüpfungen und werkzeugspezifische Ein-/Ausbauten erfassen.')
add('projects','manage','Projekte koordinieren','Projektmitglieder, Aufgaben, Leitung und Archivierung verwalten; Teileeinträge begründet stornieren. Fremde Projekte zusätzlich nur mit Gesamtübersichtsrecht.')
add('projects','correct_times','Projektzeiten korrigieren','Mitarbeiterzeiten in zugänglichen Projekten begründet korrigieren oder stornieren. Originaldaten bleiben im Projektprotokoll erhalten. Keine Änderung von Maschinenzeiten.')
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


for _action, _title, _description in (
    ('view','Einstellberichte ansehen','Einstellberichte mit Historie und zugehörigen Bildschirmfotos am Werkzeug öffnen.'),
    ('create','Einstellberichte beginnen','Einen neuen Einstellbericht oder eine neue Fassung als ungeprüfte Vorlage am Werkzeug anlegen.'),
    ('edit','Wizard und Entwürfe bearbeiten','Offene Einstellberichte manuell erfassen, Stammdatenvorschläge bestätigen und Maschinenfotos lokal auslesen. Stammdatenänderungen benötigen eigene Rechte.'),
    ('release','Geprüft abschließen','Vollständig geprüfte Einstellberichte schreibgeschützt abschließen. Dies ist keine Maschinen- oder Sicherheitsfreigabe.'),
    ('pdf_export','PDF und Ausdruck','Einstellberichte als PDF mit Prüfstatus und Quellen herunterladen und ausdrucken.'),
    ('external_ocr','Externe Fotoerkennung (Groq)','Maschinenfotos nach Einzelbestätigung an Groq senden. Zusätzlich wird das Recht zum Bearbeiten des Einstellberichts benötigt.'),
):
    add('setup_reports', _action, _title, _description)


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
