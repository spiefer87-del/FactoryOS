# Persönliche Projekte und Werkzeugreparatur-Historie

## Installation

Dieses Paket ergänzt den aktuellen FactoryOS-Stand mit Fehlerkatalog/Foto-Upload. Alle enthaltenen Dateien mit ihrer Ordnerstruktur ins Repository übernehmen. Es enthält vollständige Dateien, keinen automatisch anzuwendenden Git-Diff.

Danach auf dem Raspberry Pi:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_project_workspace.sh
```

Der Installer prüft die Voraussetzungen, stoppt den Dienst, sichert die tatsächliche SQLite-Datenbank unter `instance/backups/before_project_workspace_*.db`, ergänzt ausschließlich neue Tabellen und Berechtigungen und startet den Dienst wieder. Bei einem Migrationsfehler bleibt er zur Prüfung gestoppt. Fehlerausgabe weitergeben; nicht wiederholt Daten zurücksetzen. Die Migration ist wiederholbar. Keine Bestandsdaten werden gelöscht, keine Maschinenzeiten, Werkzeugzustände oder Lagerbestände geändert. Fotos nutzen die vorhandene Ablage unter `instance/storage/Projects/Reports` (bzw. den konfigurierten Speicherpfad); diese Ablage weiterhin regulär mitsichern.

## Rollen einrichten

Administration → Berechtigungen → Projekte:

| Recht | Verwendung |
|---|---|
| Projekte ansehen | Persönlichen Bereich und zugewiesene Projekte öffnen |
| Projekte anlegen | Eigene Projekte anlegen; zusätzlich Sichtrecht erforderlich |
| In eigenen Projekten arbeiten | Zeiten, Berichte/Fotos, Teile-Ein-/Ausbauten und Vorgangsverknüpfungen erfassen |
| Projekte koordinieren | Mitglieder, Aufgaben, Beschreibung, Leitung, Archivierung und begründete Teile-Stornos |
| Alle Projekte überblicken | Fremde Projekte lesen; nur mit Koordinationsrecht auch verwalten |
| Projektzeiten korrigieren | Zugängliche Mitarbeiterzeiten begründet ändern oder stornieren; zusätzlich Arbeitsrecht erforderlich |

Administratoren besitzen die Rechte bereits. Fachrollen werden NICHT automatisch erweitert. Projektmitglieder brauchen eigene passende Rollenrechte. Gesamtübersichtsrecht ist bewusst weitreichend: Es erlaubt auch fremde Berichte/Fotos und Zeitnachweise zu lesen. Ohne dieses Recht sind direkte URLs ebenso geschützt wie die Übersicht. Für Quellvorgänge werden zusätzlich `sampling.view` bzw. `tool_error.view` geprüft. Die Werkzeughistorie benötigt auch `tools.view`.

## Erstbenutzung

1. Projekte öffnen. Standard ist immer „Meine Projekte“; persönliche Zuordnung erfolgt serverseitig anhand des angemeldeten Kontos, nicht anhand eines gemeinsamen Browser-Speichers.
2. Bestehende Projekte bleiben erhalten. Die vorhandene Projektleitung wird als Mitglied übernommen. Als Administrator „Alle Projekte“ wählen, falls noch keine persönliche Zuordnung existiert, dann Projekt öffnen und Team/Projektleitung zuweisen.
3. Ein neues Projekt benötigt Nummer und Ziel/Beschreibung; das Projektwerkzeug ist optional. Ersteller wird Leitung und Mitglied. Projektkoordinatoren weisen weitere Mitarbeiter und Aufgaben zu.
4. Musterung oder Fehlermeldung ab zwei Zeichen nach Nummer, Werkzeug oder Beschreibung suchen und verknüpfen. Abweichende Werkzeuge müssen bewusst bestätigt werden. Der ursprüngliche Vorgang wird nicht kopiert und nicht automatisch freigegeben/geschlossen.
5. Mitarbeiterzeit starten, pausieren/beenden und bei Bedarf als neues Intervall fortsetzen. Nachträgliche Eingabe sowie begründete Korrektur/Storno sind möglich. Pro Person darf nur ein neues Projektintervall gleichzeitig laufen. Maschinenzeiten bleiben unabhängig. Uhrzeiten: Europe/Berlin; doppelte Stunden bei Zeitumstellung explizit auswählen.
6. Berichte mit Befund, Tätigkeit, Ergebnis und nächsten Schritten ergänzen. Bis zu fünf Fotos pro Bericht, lokal komprimiert, mit Zuschnitt/Zoom vor dem Upload; serverseitig erneut begrenzt. Berichte sind Nachweise und werden append-only ergänzt, nicht still überschrieben.
7. Bei Werkzeugreparatur/Wartung das tatsächliche Stammdatenwerkzeug wählen und spezifischen Ein- oder Ausbau mit Teil, Menge/Einheit, Position/Nest, optional Teile-/Seriennummer, tatsächlichem Datum, Grund/Befund und Verbleib dokumentieren. Ein Wechsel sind zwei Nachweise: altes Teil ausbauen, neues Teil einbauen. Optional jeweils den konkreten verknüpften Vorgang auswählen.
8. Am Werkzeug gibt es den Einstieg „Reparatur / Wartung · Teilehistorie“. Dort stehen werkzeugübergreifend alle Einträge aus zugänglichen Projekten. Ein Storno markiert eine Fehleingabe; es behauptet keinen tatsächlichen Gegen-Einbau oder -Ausbau. Anschließend den richtigen Eintrag neu erfassen.

## Sicherheit und Abgrenzung

- Jeder schreibende Aufruf prüft Rolle, Objektzuordnung, CSRF und Projektversion. Veraltete Seiten/Doppelklicks erfordern Neuladen; es gibt keine stille Doppelbuchung.
- Zeiten und Teilekorrekturen behalten Originaldaten und Begründung. Keine Hard-Delete-Funktion für Projektnachweise.
- Ein Archivabschluss verlangt beendete Zeiten und erledigte Aufgaben. Wiederöffnen nur berechtigt mit Begründung. Quellvorgänge behalten ihren eigenen Abschlussprozess.
- Alte `PROJEKT`-Buchungen bleiben separat sichtbar und werden nicht als neue Zeiten umgerechnet. Eigene laufende Altbuchungen lassen sich beenden; historische Reparaturen daran weiterhin über die vorhandene administrative Buchungsprüfung. Altzeiten sind nicht in der neuen Stundenkachel enthalten.
- KEIN allgemeines Ersatzteillager: Dokumentiert werden tatsächliche werkzeugspezifische Ein-/Ausbauten. Keine Lagerabbuchung, keine automatische Bestandsberechnung „aktuell eingebaut“ und keine technische Werkzeug-/Maschinenfreigabe.
- Projektübersicht: 30 Projekte pro Seite. Detail zeigt bis zu 200 neueste Zeiten, 50 Berichte, 100 Teileeinträge/Altzeiten und 50 Änderungen; Werkzeughistorie bis zu 300 Einträge. Alle gespeicherten Zeiten gehen in die neue Stundensumme ein. Historien-Paginierung und ein eigener Projektexport sind noch nicht enthalten.

## Prüfungen

`scripts/test_project_workspace.py` testet ausschließlich mit synthetischen Daten und einer In-Memory-Datenbank: Migration wiederholt, Altprojektübernahme, Nutzertrennung, Rechte/CSRF, Verknüpfungen, Aufgaben, Archivierung, Zeitüberschneidungen und Zeitumstellung, Korrektur/Storno, Werkzeugteilehistorie, Fotoverkleinerung/Fotorechte, Doppelklickschutz und Löschschutz für verknüpfte Datensätze. Der vorhandene Musterungs-Regressionslauf ist mit enthalten. Syntaxprüfungen für JavaScript und Installer sind erfolgt. Ein Test am realen Smartphone und auf der laufenden Raspberry-Pi-Installation steht nach Installation noch aus.
