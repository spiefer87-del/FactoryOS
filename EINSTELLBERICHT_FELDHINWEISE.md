# Einstellbericht: eindeutige Feldhinweise und Düsenradius

Stand: 16.11.2026. Basis: GitHub main `9e50bb7660590386ba26569173d11dcbd3e58a40`.
ZIP enthält vollständige geänderte/neue Dateien, keinen Diff.

## Änderungen

- Düsenradius akzeptiert `R40`, `R 40`, `r40,5`, `40` und `40,5`.
  Gespeichert wird weiterhin ein numerischer Millimeterwert, z. B. `40.5`.
  Die R-Schreibweise gilt ausschließlich für den Düsenradius, nicht für andere Zahlenfelder.
- Fehler nennen Schritt und Feld, bei Profilen zusätzlich Zeile und Spalte.
- Bei einem fehlerhaften Speicherversuch öffnet sich der richtige Schritt automatisch.
  Das betroffene Eingabefeld wird rot markiert, erhält eine direkte Erklärung und den Fokus.
  Auch horizontal verdeckte Profilzellen werden in den sichtbaren Bereich gerollt.
- Eine anklickbare Fehlerübersicht führt zurück zum Feld; betroffene Schritte erhalten ein Ausrufezeichen.
- Hinweise sind über `aria-invalid`/`aria-describedby` auch für assistive Technik zugeordnet.
- Fehler bei Begründungen, Datum, Einheiten, Sollwerten, Zonenaktivierung und Stammdatenzuordnung
  erhalten ebenfalls eindeutige Ziele. Bei Abschlussprüfung sind offene Felder zugeordnet.
- Korrigieren eines gemeldeten Felds entfernt seinen alten Hinweis. Beim nächsten Speichern
  wird erneut serverseitig geprüft. Es wird jeweils der erste blockierende Eingabefehler
  gemeldet; nach dessen Korrektur kann der nächste sichtbar werden.
- Gescheitertes Speichern verändert weder Datenbankstand noch Historie. Eingaben bleiben
  im geöffneten Wizard erhalten. Nicht vor dem Sichern neu laden oder die Seite schließen.

Der Screenshot allein zeigte nicht, welches Zahlenfeld betroffen war. Die anschließende
Rückmeldung hat den Düsenradius mit `R` als konkreten Auslöser identifiziert. Es wird
deshalb keine Zahl geraten und nicht pauschal Text in Zahlenfeldern zugelassen.

## Installation

ZIP entpacken und die Dateien mit gleicher Ordnerstruktur in das bestehende GitHub-Repository
hochladen. Danach auf dem Raspberry die Befehle einzeln ausführen:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_setup_report_fix.sh
```

Wizard anschließend neu laden. Neue Versionskennung lädt JavaScript und CSS erneut.
Eine Datenbankmigration und erneute Groq-/Schlüsseleinrichtung sind nicht erforderlich.
DuckDNS, Tailscale, Stammdaten und gespeicherte Berichte bleiben unverändert.

## Geprüft

Automatisierte, isolierte Datenbanktests für R-Schreibweisen, strikte andere Zahlenfelder,
exakte Fehleradressen, unveränderte Datenbank/Version/Revision nach Fehleingabe,
Profilzeilen/-spalten, aktive Temperaturzonen ohne Sollwert, Begründung und Zuordnung.
JavaScript-Tests für Schrittwechsel, Feldmarkierung/Fokus, Erhalt der getippten Werte,
Korrektur und erneutes Speichern, einschließlich Profilzellen.
Vorhandene Wizard-, OCR-, Groq- und Berechtigungstests wurden erneut ausgeführt.
Es gab dabei keinen echten Groq-Aufruf und keinen Test auf einem echten Android-Gerät.
