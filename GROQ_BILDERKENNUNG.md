# FactoryOS – externe Bilderkennung für Einstellberichte

Stand 16.11.2026. Vollständige geänderte/neue Dateien, kein Diff.
Basis: `ed62d6080a4ab0e1697b6028921fc98131c4e97b` (GitHub main).

## Installation mit Android-Terminal

1. ZIP entpacken. Die Dateien mit derselben Ordnerstruktur in das bestehende
   FactoryOS-GitHub-Repository hochladen. Nicht einen zusätzlichen ZIP-Ordner anlegen.
   Keine Datenbank, Fotos oder Schlüsseldateien hochladen.
2. Auf dem Raspberry diese drei Zeilen einzeln ausführen:

   ```bash
   cd /home/factoryos/FactoryOS
   git pull --ff-only origin main
   bash scripts/install_groq_vision.sh
   ```

3. Bei der Abfrage `FREE` eingeben und Enter drücken. Kein Editor nötig.
   Das Skript verwendet die bereits angelegte Schlüsseldatei
   `/etc/factoryos-secrets/groq.env`. Der Schlüssel wird nicht angezeigt,
   nicht in Git gespeichert und muss nicht erneut eingegeben werden.
4. FactoryOS neu laden. Im Einstellbericht in **Spritzparameter**, **Werkzeug
   und Auswerfer** oder **Temperaturen** auf **Foto-Erkennung versuchen** klicken.
   **Extern mit Groq** auswählen, Übertragung dieses Fotos anhaken, Foto auswählen.
   Bei NC5 das entsprechende Steuerungsprofil wählen.
5. Vorschläge einzeln übernehmen, am Foto prüfen und mit dem Prüf-Haken bestätigen.
   Profile benötigen zusätzlich die Aktivierung jeder Stufe/Zone. Entwurf speichern.

Der Administrator hat das neue Recht automatisch. Andere Rollen benötigen zusätzlich
zum Bearbeitungsrecht das neue Recht **Externe Fotoerkennung (Groq)**.
Keine normalen Rollen erhalten automatisch neue Rechte.

## Was geändert wird

- Serverseitige Vision-Anbindung an Groq, Modell `qwen/qwen3.8-27b`.
- Eigene Auswahl pro Erkennungsweg; Standard bleibt lokale Erkennung.
- Ausdrückliche Übertragungsbestätigung pro Foto; keine Hintergrund-Uploads.
- Schrittbezogene Zahlen/Einheiten/Profile; Soll- und Istwerte getrennt.
- Unlesbare Werte bleiben leer, keine Reparatur von `00` zu einer geratenen Zahl.
  Dosierposition null/negativ wird nicht als Vorschlag angeboten.
- Vorschläge ändern keine Parameter oder Stammdaten ohne Übernahme.
- Vollständige Profilstruktur mit leeren, nicht geratenen Zellen; Fotoquelle bleibt beim Speichern erhalten.
- Fotoquellen werden korrekt als lokal oder extern erkannt ausgewiesen.
- Geschützter Fotoabruf, Prüfstatus, Historie und bestehendes FB-18-PDF bleiben erhalten.

Die Anbindung ist zunächst ausschließlich für den Einstellbericht, nicht für den
Materialsack-Scanner. Identität, Materialdaten und weitere Freitexte bleiben im
vorhandenen Stammdaten-/Handeingabeablauf. Es werden keine Maschinen angesteuert.

## Kosten und Datenschutz

Die Anwendung kann deinen tatsächlichen Groq-Tarif nicht prüfen. Nur Free-Konto
verwenden, wenn keinerlei Kosten entstehen sollen. Keine Zahlungsdaten hinterlegen
oder auf Developer hochstufen. Die App nimmt keine Tarifänderung vor. Bei einem
bereits bezahlten Konto können Aufrufe Kosten verursachen; das lokale Limit ist
keine verbindliche Kostensperre des Anbieters.

Lokales, serverweit geteiltes Limit: **10 Versuche pro UTC-Kalendertag**. Fehlgeschlagene
Versuche zählen mit. Keine automatischen Wiederholungen, kein Wechsel auf andere
Modelle oder Anbieter. Gleiches normalisiertes Foto im gleichen Bericht und gleichen
Schritt/Steuerungsprofil verwendet das gespeicherte Ergebnis, ohne erneute Anfrage.
Groq kann zusätzlich eigene, niedrigere Kurzzeit-/Tokenkontingente durchsetzen.

Übertragen werden das normalisierte JPEG ohne EXIF und allgemeine Erkennungsanweisungen,
nicht zusätzlich die Stammdaten aus FactoryOS. Alles auf dem Foto Sichtbare wird
übertragen: daher ausschließlich den relevanten Maschinenbildschirm fotografieren.
Keine vertraulichen Kunden-/Personendaten mitfotografieren.

Groq speichert Anfragen laut Dokumentation grundsätzlich nicht für Inferenz,
kann Inhalte aber u. a. zur Fehler-/Missbrauchsanalyse vorübergehend speichern.
Im Groq-Konto **Data Controls / Zero Data Retention** prüfen und aktivieren.
FactoryOS kann die externe Kontoeinstellung nicht erzwingen. Das Foto und die
gefilterten Vorschläge werden weiterhin geschützt mit dem Bericht in FactoryOS gespeichert.

Quellen, überprüft am 16.11.2026:

- https://console.groq.com/docs/vision
- https://console.groq.com/docs/your-data
- https://console.groq.com/docs/billing-faqs
- https://console.groq.com/docs/rate-limits

## Dienstkonfiguration und Rücknahme

Das Skript legt nur `/etc/systemd/system/factoryos.service.d/50-groq-vision.conf`
an. Es ergänzt `EnvironmentFile` sowie die beiden Opt-in-Schalter, ohne den
Schlüssel in die Konfiguration zu kopieren. Abweichende bestehende Datei wird
nicht überschrieben. Nur eine neue Berechtigung wird ergänzt; keine bestehenden
Stammdaten oder Berichte werden geändert. nginx, DuckDNS und Tailscale bleiben unverändert.

Zum Abschalten im Terminal:

```bash
sudo mv /etc/systemd/system/factoryos.service.d/50-groq-vision.conf /etc/systemd/system/factoryos.service.d/50-groq-vision.conf.disabled
sudo systemctl daemon-reload
sudo systemctl restart factoryos.service
```

Der Schlüssel bleibt dabei sicher gespeichert. Lokal und manuell kann weitergearbeitet werden.
Den Inhalt der Schlüsseldatei oder die komplette Dienst-Umgebung niemals als Screenshot teilen.

## Prüfung und verbleibender Praxistest

Automatisierte Tests mit isolierter SQLite-Datenbank und simulierten Groq-Antworten:
Opt-in, Rechte, CSRF, Versionsprüfung, Soll/Ist-Trennung, Einheiten, Zahlenprüfung,
Profilquellen, sofortige Formularübernahme, keine automatischen Parameteränderungen,
Kontingentzähler, Cache, HTTP-Fehler ohne Schlüsselanzeige, keine Redirects/Retry-Schleifen.

Kein echter API-Aufruf wurde hier durchgeführt: Der Schlüssel liegt nur auf deinem
Raspberry. Erreichbarkeit, Kontoberechtigung, Geschwindigkeit und Erkennungsqualität
auf euren Maschinenfotos müssen nach Installation getestet werden. KI kann auch
plausibel aussehende falsche Zahlen liefern; alle Werte bleiben ausdrücklich ungeprüft.
Android-Kamera und Darstellung wurden nicht auf einem echten Gerät geprüft.

Testbefehle (Entwicklungsumgebung mit vorhandenen Python-Abhängigkeiten):

```bash
python scripts/test_groq_vision.py
python scripts/test_setup_ocr_fix.py
node scripts/test_setup_reports_ui.cjs
python scripts/test_permission_labels.py
```
