# Lagerverwaltung – Fertigwaren-Grundmodul

Basis: FactoryOS main dccf64e. Vollständige neue und geänderte Dateien,
keine Ersatzdatenbank. Diese Lieferung implementiert Fertigware in ganzen
Stückzahlen, nicht Rohstoff-/Kilogrammlager, Bewertung oder Finanzbuchhaltung.

## Installation

Dateien mit Verzeichnissen nach GitHub übernehmen, dann auf dem Pi:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_inventory.sh
```

Der Installer prüft die vorhandene SQLite-Struktur, stoppt FactoryOS, sichert
instance/factoryos.db samt vorhandenen WAL-Dateien unter
/home/factoryos/backups/inventory_DATUM_UHRZEIT und ergänzt ausschließlich neue
Lagertabellen, Schutztrigger und Berechtigungsdefinitionen. Anschließend wird
der Dienst gestartet. Bei einem Upgradefehler bleibt er zur Prüfung gestoppt.
Wiederholtes Ausführen erzeugt keine Bestände und keine doppelten Rechte.
Bestehende Rollen erhalten keine zusätzlichen Rechte. Admin hat gemäß der
bisherigen FactoryOS-Regel Zugriff. Für Fachrollen „Lager ansehen“ zusammen
mit den bewusst benötigten Buchungsrechten zuweisen.

## Erster Test mit einem Auftrag

1. Hauptmenü **Lager** öffnen, unter Lagerplätze z.B. „HALLE1-A-01“ anlegen.
2. Unter Produktionsübergaben stehen ausschließlich bestätigte Gutmengen aus
   Mengenmeldungen bzw. dem endgültigen Auftragsabschluss. Prognosen und
   Auftrags-Sollmengen sind keine Lagerquelle. Ein endgültiger Abschluss
   ersetzt die zuvor gemeldeten Summen; er wird nicht zusätzlich gezählt.
3. „Produktionsübergabe“: Auftrag, exakt zugehörigen Stammdatenartikel,
   Los-/Chargen-/Behälterkennung und tatsächlich übergebene Teilmenge bestätigen.
   Die offene Übergabe ist noch kein physischer Lagerbestand. Der Auftrag
   darf noch laufen, sofern tatsächlich bestätigte Gutmeldungen existieren.
4. „Lagerannahme“: Los, tatsächliche Teilmenge und Ziellagerplatz bestätigen.
   Sie wird zunächst gesperrt eingebucht. Abweichende Restmengen bleiben offen.
   Vor der Annahme festgestellten Ausschuss separat über „Ausschuss vor
   Lagerannahme“ erfassen – nicht als Lagerabgang eines nie eingebuchten Teils.
5. Nach tatsächlicher Prüfung separat „Bestand freigeben“ buchen. Der Prüfnachweis
   gehört in Begründung/Beleg. Es gibt keine automatische QS-Freigabe durch
   einen fertigen Auftrag oder einen freigegebenen Prüfplan.
6. Für Auslieferungen freigegebenen Bestand mit Empfänger/Versandbeleg reservieren,
   kommissionieren und den tatsächlichen Versand bestätigen. Teilversand und
   die Freigabe nicht benötigter Restreservierungen sind möglich.
7. Erst Versand reduziert den physischen Bestand. Rücknahmen benötigen den
   Bezug zur Versandbuchung und gehen wieder in den Sperrbestand. Sie öffnen
   keine erledigte Reservierung automatisch erneut.

## Mengen und Korrekturen

- Verfügbar = freigegebener physischer Bestand minus offene Reservierungen.
  Gesperrter Bestand ist physisch vorhanden, aber nicht versandfähig.
- Umlagern erhält die Gesamtmenge und den Status. Reservierte Ware lässt sich
  weder verschrotten noch anderweitig verbrauchen; erst Reservierung auflösen.
- Produktionsausschuss, Ausschuss vor Lagerannahme und Lagerausschuss werden
  getrennt geführt. Gesperrte Ware ist noch kein Ausschuss.
- Lagerausschuss reduziert vorhandene Ware mit Begründung. Er erzeugt keine
  zweite Produktionsausschussmeldung und verändert keine alten Endmengen.
- Annahmen, Übergabeausschuss, Umlagerungen, Sperren/Freigaben, Lagerausschuss
  und Erstbestände können vollständig gegengebucht werden, soweit der heutige
  Bestand dies zulässt. Mengen müssen der Originalbuchung entsprechen.
- Eine vollständig offene, noch nicht verbrauchte Übergabe kann über
  „Unübernommene Übergabe stornieren“ korrigiert und neu erfasst werden.
  Bereits übernommene Mengen zuerst fachlich rückabwickeln. Ein Storno löscht
  den ursprünglichen Eintrag nicht.
- Versand wird über eine nachvollziehbare Rücknahme korrigiert; Reservierungen
  über Freigabe ihrer Restmenge. Doppelte Gegenbuchungen sind gesperrt.
- Vorhandene echte Altbestände können als „Erstbestand“ mit eigenem Los und
  Beleg im Sperrbestand erfasst werden. Dieselben Teile niemals zusätzlich als
  Produktionsübergabe übernehmen. Der Installer erfindet keine Altbestände.

## Nachweise und technische Sicherungen

Journal und Einzelbuchungsansicht enthalten Benutzer/Zeitpunkt UTC, Los,
Artikel-/Werkzeug-/Auftragssnapshot, Mengen, Lagerplätze/Statuswechsel, Grund,
Bezugsbuchung und eindeutige Buchungskennung. Produktionsübergaben halten
zusätzlich die verwendeten Mengenmelde-IDs bzw. die Abschluss-ID fest.

Einträge, Bewegungszeilen und Losursprünge werden nicht überschrieben oder
gelöscht. ORM-Sperren und SQLite-Trigger schützen UPDATE/DELETE. Dies ersetzt
keine abgesicherten Datenbankrechte, Backups oder kryptographische Archivierung.
Artikel und Aufträge mit Lagerbezug bleiben rückverfolgbar. Verwendete
Produktionsmeldungen sind nach der Übergabe gegen Änderung/Löschung geschützt.
Endgutmenge darf bestätigte aktive Übergaben nicht unterschreiten.

Alle Lagerbefehle werden gemeinsam mit Produktionsabschlüssen serialisiert
und atomar verbucht. Eindeutige Kennung plus Inhaltsprüfung schützt vor
Doppelklicks; eine Lagerrevision schützt vor veralteten Formularen. Mengen,
Bestand und Reservierungen werden innerhalb derselben Transaktion geprüft.
Fehler rollen auch bereits geschriebene Bewegungszeilen zurück. Formulare
erhalten Eingaben und zeigen Begründungen. GET-Aufrufe erzeugen keinen Bestand.

## Prüfstand und Abgrenzung

Lokal mit synthetischer SQLite-Datenbank geprüft: additive Migration aus
vorhandener Struktur zweimal, Teilannahmen, alle drei Ausschussstufen,
Sperr-/Freigabeablauf, Überreservierung, Kommissionierung, Teilversand,
Rücknahmegrenzen, Umlagerung, Gegenbuchung, Erstbestandkorrektur,
Übergabestorno, exakte Wiederholung, veraltete Formulare, atomarer Fehlerfall,
Journal-Löschschutz, HTTP-Seiten, CSRF, Leserecht ohne Schreibrechte und zwei
konkurrierende Reservierungen aus unabhängigen Sitzungen. Bestehende Tests für
Auftragsabschluss und Rechteverwaltung ebenfalls erfolgreich ausgeführt.

Bitte zunächst mit einem echten Testauftrag und kleinen bestätigten Teilmengen
gegen eure physische Zählung prüfen. Endgültige mobile Darstellung und Abläufe
im Betrieb benötigen eure Abnahme. Keine ISO-Zertifizierungs-/Normkonformitäts-
zusage; das ist eine nachvollziehbare technische Grundlage. Kein GS1-EPCIS-
Datenaustausch, keine SSCC-/Barcode-Etiketten, keine Lagerbewertung,
Lieferdokumenterstellung oder vollständige Inventurautomatik in dieser Lieferung.
Empfänger/Versandbeleg wird als Referenz erfasst, nicht als neuer ERP-Kundenauftrag.
DuckDNS, Tailscale, OCR und elektrische Maschinenfunktionen bleiben unverändert.
