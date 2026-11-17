# Persönliches Dashboard und Lager-Navigation

Basis: main eb704af. Dieses ZIP enthält vollständige neue/geänderte Dateien.
Keine Bestands- oder Produktionsdatenänderung, keine neuen Rollenrechte und
keine Datenbankmigration. Die vorhandene Tabelle user_preferences wird benutzt.

## Installation

Dateien mit Verzeichnisstruktur nach GitHub übernehmen und am Pi ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_personal_dashboard.sh
```

Der Installer prüft die vorhandene Profileinstellungstabelle und startet den
Dienst neu. Danach vollständig neu laden. Sollte die Tabelle fehlen, zunächst
das bereits bestehende Profilverwaltungs-Update installieren.

## Bedienung

- In der linken Navigation steht Lager jetzt unmittelbar unter Produktion.
- Das Standard-Dashboard enthält Lager, sofern der Benutzer Lager sehen darf.
- „Dashboard anpassen“ ist direkt auf dem Dashboard und unter „Mein Profil“
  erreichbar. Hauptbereiche und Unterseiten lassen sich individuell auswählen,
  z.B. Stammdaten → Werkzeugliste oder Produktion → Maschinen-Timeline.
- Ausgewählte Kacheln stehen in einer Vorschau. Am PC am Griff ziehen; beim
  Ablegen in der oberen/unteren Hälfte wird davor/dahinter einsortiert.
- Auf dem Handy oder per Tastatur funktionieren ↑ und ↓. Jede Kachel lässt
  sich entfernen; Kacheln werden über die Auswahl wieder hinzugefügt.
- Erst „Dashboard speichern“ persistiert die Reihenfolge und Auswahl im
  angemeldeten Benutzerkonto. „Abbrechen“ verwirft den Entwurf.
- „Standard wiederherstellen“ speichert die aktuell berechtigte Standardauswahl.
  Ein bewusst leeres Dashboard ist ebenfalls möglich; die Sidebar bleibt.
- Ohne JavaScript sind Auswahl und Positionsnummern als Formular verfügbar.

Die Einstellungen werden nach erneutem Anmelden bzw. auf anderen Geräten
geladen. Sie werden nicht nur im Browser gespeichert. Bereits offene Seiten
nach Änderungen bitte neu laden. Änderungen an Tabellenansichten, Darstellung
und Dashboard verwenden getrennte Einstellungsbereiche.

## Rechte und Schutz

Der Katalog ist eine serverseitige Liste fester Ziele, keine frei eingebbaren
URLs. Sowohl angebotene als auch angezeigte Kacheln werden bei jedem Laden
gegen die aktuellen Rechte geprüft. Manipulierte Speicherversuche mit fremden,
unbekannten oder doppelten Kacheln werden abgewiesen. Das Dashboard gewährt
niemals Zugriff auf einen eigentlich gesperrten Bereich.

Nach Rechteentzug verschwindet das betreffende Ziel aus Dashboard und Auswahl.
Die bisherige Einstellung wird durch das bloße Lesen nicht überschrieben;
bei erneuter Berechtigung kann die gespeicherte Auswahl wieder sichtbar werden.
Ein Speichern ersetzt die Auswahl ausdrücklich durch die aktuell ausgewählten
berechtigten Ziele. Benutzerkonto und Version sind gebunden, CSRF wird geprüft.
Ein Konflikt mit einem zweiten Fenster wird angezeigt, nicht automatisch
überschrieben. HTML bleibt privat und nicht zwischenspeicherbar.

## Lokale Prüfung

Flask-Tests mit zwei unterschiedlich berechtigten Benutzern: getrennte Daten,
zweites Gerät, Rechteentzug/-wiederherstellung, manipulierte Nutzdaten, doppelte
Kacheln, unzulässige URLs, CSRF, Kontowechsel, veraltete Version, Formular ohne
JavaScript, leere Auswahl, Lager-Standardkachel und Sidebar-Reihenfolge.
Bestehende Profil-, Berechtigungs- und Rechtebeschriftungstests erfolgreich.
JavaScript-Test: Hinzufügen/Entfernen, ↑/↓, Drag-and-drop ans Listenende und
Synchronisation der gespeicherten Reihenfolge. Responsive Layoutregeln sind
enthalten; die endgültige Darstellung auf eurem Android-Gerät bitte prüfen.

DuckDNS, Tailscale, Lagerbuchungen, Maschinenbedienung und OCR bleiben unverändert.
