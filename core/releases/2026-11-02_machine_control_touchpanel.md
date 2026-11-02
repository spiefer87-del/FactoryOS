# FactoryOS – Maschinenbedienung und Touchscreen-Vorbereitung

Basis: main 3991e31. Vollständige geänderte/neue Dateien, kein Git-Diff.

## Oberfläche

- Maschinenname in Timeline oder aktueller Statuskarte anklicken: Bedien-Pop-up.
- Große Touch-Buttons für Auftrag starten, Pause/Fortsetzen, Rüsten/Abrüsten,
  Störung/Entstören, Wartung, Sonstiges und Beenden/Stoppen.
- Auftragsauswahl mit Suchfilter, Werkzeugauswahl, Störgrund und Beschreibung.
- Maschinenzustand, Auftrags-/Werkzeugbezug, Beginn und Bediener sichtbar.
- Letzte 30 neue Befehle mit Zustandswechsel und Beschreibung aufklappbar.
- Link zur eigenständigen Touchscreen-Seite im Pop-up. Anmeldung bleibt nötig.
- Nach Schließen eines geänderten Bedienfelds lädt die Timeline neu.
- Frühere Start-/Stopp-/Rüstlinks führen zur Bedienung, statt aktiv belegte
  Maschinen still umzubuchen. Ein Start erfolgt erst im Bedienfeld mit Bestätigung.
- Musterungsbuchung beenden öffnet jetzt ebenfalls die Maschinenbedienung.
  Nach Stoppen Ergebnisse ergänzen und Musterung wie bisher separat prüfen/abschließen.

## Fachliche Leitplanken

Entstören startet keinen Vorgang automatisch. Bei unterbrochenem Vorgang folgt
PAUSE; ausdrückliches Fortsetzen ist notwendig. Aufträge bleiben während
Unterbrechungen reserviert. Rüsten beenden führt zu FREI und erfordert anschließend
einen eigenen Produktionsstart. Stoppen beendet nur den Maschinenvorgang, nicht
den Auftrag oder eine QS-Freigabe. Keine Mengen werden automatisch erzeugt.

Ein Auftrag kann nicht gleichzeitig auf zwei Maschinen laufen/reserviert sein.
Inaktive Maschinen, fertige/gesperrte Aufträge, unzulässige Musterungszustände,
fehlender Sollzyklus und widersprüchliche aktive Altbuchungen werden geprüft.
Altbuchungen werden nicht automatisch bereinigt. Zeitprognosen verwenden weiterhin
nur Produktions-/Musterungsintervalle und den bestehenden Arbeitskalender.

Ein Befehl erzeugt atomar Zeitintervall, Fortsetzungskontext, Version, UUID-Beleg
und Benutzerprotokoll. Doppelt gesendete identische Befehle erzeugen keine
Doppelbuchung. Veraltete Fenster erhalten einen Konflikt statt stiller Ablösung.
CSRF und aktionsbezogene Rechte werden serverseitig geprüft. Auch der frühere
Projekt-Stopp-Pfad kann keine Maschinenbuchungen mehr direkt schließen.
Startzeitkorrekturen verwenden dieselbe Sperre. Aufträge mit Buchungen sowie
Maschinen mit Historie können nicht gelöscht werden; Maschinen stattdessen deaktivieren.

## Rechte

Bestehende Rechte gelten weiterhin: Produktion ansehen, Start/Fortsetzen,
Stop/Pause/Störung, Rüsten und sonstige Maschinenereignisse. Für Fortsetzen eines
Rüst-/Wartungs-/sonstigen Vorgangs gilt das zugehörige Fachrecht.
Neu: `production.clear_fault` (Entstören) und `production.maintenance` (Wartung).
Admin hat Zugriff. Fachrollen erhalten keine neuen Rechte automatisch;
in der Rechteverwaltung bewusst freischalten. Bedienseite benötigt production.view.

## Datenbank und Installation

Neu: machine_control_lock, machine_control_states, machine_control_commands.
Bestehende Buchungen und Mengen bleiben unverändert. Upgrade ist wiederholbar.
Vor Strukturänderungen Dienst stoppen und DB einschließlich WAL/SHM sichern.
Installer prüft vorher vorhandene Tabellen und erkennt die vorhandene Python-venv.
Für diese Installation wird die bisherige instance/factoryos.db vorausgesetzt;
bei abweichender DB-Konfiguration Sicherung und Installation vorher anpassen.

Nach Übernahme der ZIP-Inhalte mit identischen Pfaden in GitHub:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_machine_control.sh
```

Danach App neu laden, auf Testmaschine zuerst Rüsten → Beenden → Auftrag starten
→ Störung → Entstören → Fortsetzen → Stoppen durchspielen. Prüfen, dass Entstören
in PAUSE bleibt und nur eine aktive Buchung existiert. Neue Rechte für Fachrollen
zuweisen. Keine neue APK erforderlich. DuckDNS und Tailscale bleiben unverändert.

## Controller-Vorbereitung – bewusst ohne Hardwarezugriff

Ein gemeinsamer Befehlsdienst, Versionsprüfung, UUID-Quittungen, gespeicherter
Fortsetzungskontext und Herkunftsfeld bilden die Basis für spätere Geräteadapter.
Verbindlicher Rahmen: docs/machine_control_controller_contract.md.
Es gibt jetzt keine Geräte-Registrierung, kein offenes Controller-API und keine
elektrische Ansteuerung. Der Zustand stammt aus manuellen Bedienerbuchungen,
nicht aus Maschinensensoren. Not-Halt/Schutzfunktionen bleiben außerhalb FactoryOS.

## Prüfung

Isolierte Tests mit synthetischer SQLite-Datenbank: Zustandsfolgen, Rückkehr nach
Störung aus Produktion/Pause/Rüsten/Wartung, Rechte, CSRF, UUID-Replay, veraltete
Revisionen, konkurrierende Startversuche, atomarer Rollback bei Protokollfehler,
Intervallkontinuität, Altbuchungskonflikte, Upgrade-Wiederholung, Musterungsregeln,
Auftragsstatistik und bestehende Rechteverwaltung. Konkurrenztests verwenden
unabhängige Datenbanksitzungen in Threads gegen eine temporäre SQLite-Datei.
Zusätzlich Python-/JavaScript-Syntax und Patch-Whitespace geprüft.
Kein Zugriff auf produktive Raspberry-Datenbank oder echte Maschinen. Kein
automatisierter Browser-/Touchscreen-Render-Test; Geräteabnahme vor Ort erforderlich.
