# Materialetikett: Hersteller und zweisprachige Angaben

Basis: FactoryOS main 87d2455. ZIP enthält vollständige geänderte/neue Dateien,
keinen Git-Diff. Dateien mit gleicher Ordnerstruktur übernehmen.

## Änderungen

- Hersteller wird zuerst in den Vorschlägen angezeigt. Nicht erkannte Kernfelder
  (Hersteller, Bezeichnung, Materialart, Kunststoffart) bleiben als leere,
  nicht ausgewählte Prüffelder sichtbar. Weitere fehlende Angaben stehen in
  einem eigenen aufklappbaren Bereich.
- Zweisprachige Beschriftungen mit Werten daneben oder darunter werden erkannt,
  z. B. Hersteller/Manufacturer, Typ/Type, Farbe/Color, Partie/Lot.
- Herstellerkopf und Handelsname werden mit dem separat gedruckten Typ kombiniert.
  Druckschriftvarianten bekannter Hersteller-/Handelsnamen können vorsichtig
  normalisiert werden. Solche Vorschläge bleiben gelb und nicht ausgewählt.
  Wörterlisten dienen nur der Schreibweise: keine Zuordnung von Handelsnamen
  zu Hersteller oder chemischer Kunststoffart.
- ENVALIOR – DURETHAN + Typ B30S ergibt die prüfbaren Vorschläge Hersteller
  ENVALIOR und Bezeichnung DURETHAN B30S. Eine beschädigte OCR-Schreibweise
  wird ausdrücklich als Normalisierung gekennzeichnet.
- Rein numerische Farbangaben wie 000000 bleiben als Farbnummer einschließlich
  führender Nullen erhalten. Keine erfundene Farbbezeichnung oder RAL-Zuordnung.
- Partie/Los und Sackgewicht erscheinen separat nur zur Kontrolle. Auch typische
  OCR-Fehllesungen wie „Perle“ werden nicht mehr als Materialname vorgeschlagen.
  Kein Übertragen von Charge oder Sackgewicht in Materialidentität oder Bestand.
- Beide vorhandenen Tesseract-Layouts (sparse/block) werden geprüft, statt beim
  ersten Text mit 20 Zeichen abzubrechen. Auswahl nach brauchbaren Feldern und
  Lesbarkeit, keine Vermischung widersprüchlicher Lesungen. Falls nur der zweite
  Versuch scheitert, bleibt ein verwertbarer erster Versuch erhalten.

## Grenzen / Datenschutz

Lesbare oder ausdrücklich beschriftete Angaben sind Vorschläge, keine fachlich
geprüften Daten. Fehlende Angaben können nicht aus einem Foto rekonstruiert
werden. Insbesondere Kunststoffart, Sicherheits- und Verarbeitungsvorgaben
erfordern bei fehlendem Aufdruck ein Datenblatt bzw. manuelle Prüfung.
Unbekannte Hersteller können über eine ausdrückliche Hersteller-Beschriftung
erkannt oder manuell ergänzt werden. Unsichere Herstellerköpfe bleiben offen.

Weiterhin lokale OCR, kein Cloud-Dienst, keine neuen API-Schlüssel, keine
permanente Fotospeicherung und keine Datenbankänderung. Bestehende Berechtigungen,
CSRF, Größenlimits, Prozesssperre, Zeitlimits 10 + 8 Sekunden und ein OCR-Thread
bleiben erhalten. Keine Anpassung an DuckDNS, Tailscale oder APK notwendig.

## Installation

Nach Übernahme der Dateien nach GitHub auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_material_label_parser.sh
```

Der Installer prüft Python/OCR und startet den FactoryOS-Dienst neu. Er installiert
keine Pakete und verändert weder Dienstkonfiguration noch Datenbank. Formular
danach neu öffnen und Foto erneut auslesen.

## Prüfung

- Parserfälle: zweisprachige Kopf-/Mehrzeilenangaben, beschädigte manuell
  übertragene OCR aus der Fehlermeldung, explizite unbekannte Hersteller,
  mehrere Hersteller, Farbnummern mit Nullen, Masterbatch, Polymer-Mehrdeutigkeit,
  Produktcode-Abgrenzung, fehlende Werte, Charge-/Gewichtsabgrenzung.
- Echte lokale Tesseract-Läufe auf generierten JPEG-Testetiketten, darunter ein
  ENVALIOR/DURETHAN/B30S-Layout; zweiter Versuch mit Timeout behält ersten Text.
- Bestehender Ende-zu-Ende-Test: API, CSRF/Rechte, Dublettenhinweise,
  keine Speicherung vor finalem Absenden, temporäre Dateien, OCR-Sperre/Timeout.
- JavaScript-Logiktest mit DOM-Stubs und Syntaxprüfungen.
- Kein Test der Originalaufnahme in voller Auflösung, kein Android-Kamera- oder
  Raspberry-Lauf vor Ort. Die Originalaufnahme war nur in einem App-Screenshot
  verfügbar; der nächste reale Sacktest bleibt erforderlich.
