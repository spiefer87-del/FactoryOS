# Verständliche deutsche Beschriftungen in der Rechteverwaltung

Basis: main 014becc. ZIP mit vollständigen geänderten/neuen Dateien samt
Installationsskript und Test. Keine Datenbank enthalten.

Alle aktuell von der Zugriffspolitik verwendeten Rechte erhalten zentral gepflegte
deutsche Titel und konkrete Beschreibungen. Beispiele:

- Articles → Artikel; Customers → Kunden; Materials → Materialien und Farbbatches.
- Create / Edit / Delete / View → Anlegen / Bearbeiten / Löschen / Ansehen.
- Production / Setup → Produktion und Maschinenbuchung / Rüstvorgänge erfassen.
- Materials / Documents → Dokumente verwalten, mit Erklärung zu Upload/Archiv und
  dem getrennten Leserecht für Downloads.
- Sampling / Release → Abschließen und Freigaben pflegen, mit Hinweis, dass die
  fachlichen Abschlussprüfungen einschließlich Erstbemusterung weiter gelten.

Bereiche werden nach deutschem Namen sortiert, Rechte innerhalb eines Bereichs
nach Tätigkeiten (zuerst Ansehen/Anlegen/Bearbeiten, Löschrechte am Ende).
Bekannte Systemrollen erhalten verständliche Anzeigenamen; selbst benannte Rollen
behalten ihren Namen. Gespeicherte Rollen-/Berechtigungsnamen bleiben unverändert.
Die technischen Kennungen sind nur im aufklappbaren Bereich „Technische Kennung“
sichtbar. Unbekannte zusätzliche Rechte erhalten eine neutrale, nicht erfundene
Beschreibung. Eine vorhandene verständliche individuelle Beschreibung wird für
solche unbekannten Rechte weiterhin angezeigt; rohe Kennungen nicht als Beschreibung.

Keine Rechte werden vergeben, entzogen, umbenannt oder funktional verändert.
Die Datenbankbeschreibungen werden nicht überschrieben; die Anzeige verwendet den
zentralen Textkatalog. Checkbox-IDs, Formulardaten, CSRF, Matrix-Version und
geschützte Adminrechte bleiben unverändert.

## Installation

ZIP-Dateien mit unveränderten Repository-Pfaden in GitHub übernehmen und committen.
Dann auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_permission_labels.sh
```

Bei Fehlern oder Konflikten stoppen und Ausgabe weitergeben. Kein Datenbankupgrade,
keine neuen Abhängigkeiten und keine erneute Sitzungsschlüsseländerung. Danach
Rechteverwaltung mit Strg+F5 neu laden.

## Prüfung

`scripts/test_permission_labels.py` nutzt eine isolierte SQLite-Testdatenbank und
prüft vollständige Textabdeckung aller aktiven Rechte, deutsche Gruppen/Titel,
neutrale unbekannte Rechte, Escaping, unveränderte IDs/Rollenrechte/DB-Beschreibungen
und geschützte Admin-Checkboxen. Führt auch die bestehenden Rechte-Regressionen
mit 187 verweigerten Aufruf-/Methodenkombinationen aus. Python-Kompilierung,
Shell-Syntax, Diff und ZIP geprüft. Kein Raspberry-Livedatenzugriff oder echter
Browser-Layouttest; fachfremde OpenCV-Erkennung nur in Tests gestubbt.
