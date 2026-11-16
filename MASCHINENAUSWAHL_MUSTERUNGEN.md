# FactoryOS – Musterungs- und Werkzeugauswahl an der Maschine

Stand: 16.11.2026. Basis: GitHub main `049797749d07c6e4e6cc161a7bacd73eb7959cd8`.
ZIP mit vollständigen geänderten/neuen Dateien, kein Diff.

## Musterungen werden sichtbar

Bisher blendete die Maschinenbedienung alle Musterungen aus, die nicht bereits
„In Bearbeitung“/„In Prüfung“ **und** genau dieser Maschine zugeordnet waren.
Zusätzlich waren Entwurf/Nacharbeit über den internen Auftragsstatus gesperrt und
dadurch aus der Liste verschwunden.

Jetzt werden offene Musterungen einschließlich Entwurf, Nacharbeit, unzugeordneter
Musterungen und Musterungen anderer Maschinen angezeigt. Beispiele:

- `M-100 · Musterung · Entwurf · Maschine noch nicht zugeordnet`
- `M-101 · Musterung · In Bearbeitung · ⚠ Für B 300 I vorgesehen – Wechsel bestätigen`

Erfolgreich abgeschlossene/stornierte Musterungen bleiben ausgeschlossen.
Bei einer fremden Planwarteschlange steht zusätzlich dabei, auf welcher Maschine
sie eingeplant ist. Fertigungsaufträge behalten ihre bisherigen Planungsfilter.

## Bewusst vorbereiten statt unbemerkt starten

Nach Auswahl einer noch nicht passenden Musterung erscheint **Musterung für diese
Maschine vorbereiten**. Die Folgeseite zeigt Auftrag, Werkzeug, bisherige Maschine,
Zielmaschine, Sollmenge und Zykluszeit.

Bei einer anderen bisherigen Maschine ist ein **zusätzlicher Bestätigungshaken für
den Maschinenwechsel** Pflicht. Danach wird die Zuordnung protokolliert geändert.
Entwurf/Nacharbeit werden auf „In Bearbeitung“ gesetzt; „In Prüfung“ bleibt als
Bearbeitungsstatus erhalten, falls nur die Maschinenzuordnung geändert wird.

Dieser Schritt startet weder Rüsten noch Produktion. Werkzeugbestand, Zeitbuchungen,
Qualitätsprüfungen, Prüfergebnisse und Kundenfreigaben werden nicht geändert.
Anschließend die konkrete Werkzeugnummer bestätigen und den gewünschten Vorgang starten.

Eine laufende/pausierte Musterung auf einer anderen Maschine kann nicht übernommen
werden. Ebenso werden fremde Reservierungen und Planwarteschlangen nicht heimlich
aufgehoben. Eine fremde Warteschlange muss die berechtigte Fertigungsleitung zuerst
regulär in der Auftragsplanung ändern; die Vorbereitungsseite verlinkt dorthin.
Gesperrte bereits aktive Musterungen werden nicht über die Vorbereitung entsperrt.

Vorbereitung und Maschinenwechsel benötigen die vorhandenen Rechte **Musterungsaufträge
bearbeiten** (`sampling.edit`) und **Produktion ansehen** (`production.view`). Es werden
keine zusätzlichen Rechte automatisch vergeben. Version und Maschinenstand werden
serverseitig erneut geprüft, Änderungen an Auftrag/Musterung werden protokolliert.

## Konkrete Werkzeugnummer statt „Aus Auftrag übernehmen“

Das Werkzeugfeld zeigt eine tatsächliche Nummer mit Herkunft:

- Werkzeugstamm des Musterungsauftrags;
- gespeichertes Werkzeug des Fertigungsauftrags;
- eindeutige Werkzeugzuordnung im Artikelstamm;
- bestätigter montierter Bestand oder letzter gespeicherter Werkzeugbezug.

Der Vorschlag wird sichtbar vorausgefüllt, bleibt aber **unbestätigt**. Der Einrichter
setzt den Haken **Werkzeug … vor Ort geprüft – diese Nummer bewusst übernehmen**.
Bei Änderung der Nummer oder des Auftrags wird die alte Bestätigung zurückgesetzt.
Der Server prüft den Haken und die dazugehörige genaue Werkzeugnummer ebenfalls.

Alternativ kann eine eigene vorhandene Werkzeugnummer eingetippt oder aus der
Stammdaten-Vorschlagsliste gewählt werden. Nicht vorhandene Nummern werden abgewiesen,
nicht automatisch angelegt. Mehrdeutige Artikel-Werkzeugzuordnungen werden nicht geraten.
Beim Produktionsstart bzw. Rüsten mit Auftragsbezug muss das Werkzeug zur gespeicherten
Auftragszuordnung passen. Für reine manuelle Rüstvorgänge **Ohne Auftrag** wählen.

## Abrüsten nach Auftragsende

Das Werkzeug bleibt nach Auftragsabschluss im unabhängigen Werkzeugbestand bzw.
als ungeprüfter letzter Bezug erhalten. Im Auswahlbereich steht beispielsweise
**Werkzeug COR150 zum Abrüsten vorausfüllen**. Damit wird genau diese Nummer ins
Eingabefeld übernommen; sie muss anschließend bewusst bestätigt werden.

Abrüsten braucht keinen offenen Auftrag. Ein eventuell noch ausgewählter Folgeauftrag
wird für den Abrüstbefehl ignoriert; Werkzeug und tatsächlicher Bestand bleiben die
maßgebliche Prüfung. Ein bestätigter leerer Bestand wird nicht durch einen alten
Werkzeugvorschlag überschrieben. Die bisherigen Rüsthistorien, Doppelbelegungsprüfungen
und Bestandsprüfungen bleiben wirksam. Die Bestätigung der Werkzeugwahl ist keine
automatische Montagebestätigung und keine elektrische Maschinen-/Sicherheitsfreigabe.

Ohne JavaScript stehen Vorschau-Buttons zum Laden von Auftrags-/Werkzeugwahl bereit;
auch dort findet vor einem echten Befehl die Prüfung auf vorhandene Stammdaten statt.

## Installation

ZIP entpacken und Dateien in gleicher Ordnerstruktur in das bestehende GitHub-Repository
hochladen. Danach im Handy-Terminal diese einzelne Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_machine_selection.sh
```

Das Skript prüft die vorhandene Struktur und startet den Dienst neu. Keine
Datenbankmigration und keine automatische Änderung bestehender Musterungen.
Vorbereitung/Umzuordnung erfolgen erst durch den bewussten Benutzerbefehl.
Danach Maschinenbedienung neu laden. Groq-Schlüssel, DuckDNS und Tailscale bleiben unverändert.

## Prüfungen

Automatisierte Tests mit isolierter Datenbank für Anzeige fremder/unzugeordneter
Musterungen, separate Wechselbestätigung, Version/CSRF/Rechte, unveränderte QC-Daten,
Schutz aktiver und eingeplanter Aufträge, tatsächlichen Musterungsstart nach Vorbereitung,
Werkzeugvorschläge, fehlenden/falschen Bestätigungshaken, unbekannte Stammdaten,
manuelle auftragslose Rüstwahl, Abrüsten nach Abschluss sowie read-only Vorschau.
JavaScript-Tests prüfen Bestätigungsreset, Auftragswechsel, Abrüstvorschlag und
aktionsbezogene Prüfung. Maschinenbedienungs-, Werkzeugbestands-, Abschluss-, Planungs-
und Berechtigungstests wurden erneut ausgeführt. Kein Test auf echtem Android-Gerät.
