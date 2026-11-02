# Passwortwechsel in „Mein Profil“

Basis main f28e69a. Vollständige geänderte/neue Dateien mit Repository-Pfaden,
Installationsskript und Tests. Keine Datenbank und keine Passwörter im ZIP.

## Bedienung

Benutzernamen rechts oben anklicken, Bereich „Passwort ändern“ öffnen:
aktuelles Passwort eingeben, neues Passwort zweimal eingeben und bestätigen.
Neues Passwort: 12–128 Zeichen, nicht ausschließlich Leerzeichen, anders als zuvor.
Keine Pflicht für bestimmte Sonderzeichenklassen. Lange einzigartige Passphrase
oder Passwortmanager empfohlen. Passwörter werden nicht getrimmt, daher
funktionieren bewusst gesetzte Rand-Leerzeichen auch bei der Anmeldung.

Augensymbol pro Eingabefeld zeigt ausschließlich die gerade eingegebene
Zeichenfolge. Das gespeicherte Passwort ist nicht abrufbar, es bleibt ein
Werkzeug-Passwort-Hash wie bisher. Keine Klartextspeicherung, kein Klartext/Hash im
Änderungsprotokoll. Das Protokoll erfasst nur „password_change“ / Ereignis bestätigt.
Passwortfelder sind nach Fehlern wieder leer und werden nicht aus Requests befüllt.
Ohne JavaScript bleiben die Eingaben maskiert und der Passwortwechsel funktioniert.
Bei Tabwechsel, Verlassen der Seite oder Absenden werden geöffnete Sichtanzeigen
wieder maskiert. Übliche Browser-Passwortmanager werden über autocomplete unterstützt.

Nach Erfolg wird die aktuelle Sitzung inklusive möglichem Remember-Cookie beendet;
Anmeldung mit dem neuen Passwort erforderlich. Persönliche Darstellungs-/Spalten-
Einstellungen bleiben in der Datenbank unverändert erhalten.
Andere bereits angemeldete Browser-/Gerätesitzungen werden vom bestehenden
FactoryOS-Sitzungssystem NICHT automatisch widerrufen. Dies ist keine Funktion
„auf allen Geräten abmelden“. Auch eine globale Brute-Force-Sperre bzw.
Login-Ratebegrenzung wird durch diesen gezielten Patch nicht ergänzt.
Bei vergessenem Altpasswort bleibt das vorhandene administrative Zurücksetzen nötig.
Für den Passwortwechsel eine sichere HTTPS-Verbindung verwenden.

## Sicherheitsgrenzen

Nur aktive angemeldete Benutzer; ausschließlich Änderung des eigenen Kontos.
CSRF und versteckte Kontozuordnung schützen vor Fremdrequests und alten Tabs nach
Benutzerwechsel. Aktuelles Passwort wird serverseitig geprüft. Ein bedingtes
Datenbankupdate auf ID, Aktivstatus und bisherigen Hash verhindert, dass ein
zwischenzeitlicher Passwort-/Kontowechsel blind überschrieben wird.
Hash wird mit der bestehenden Werkzeug-Funktion erstellt; keine neuen
Kryptografie-Abhängigkeiten. Username/Rolle/Berechtigungen werden nicht geändert.
Profilantworten bleiben private/no-store. Passwortänderung ausschließlich per POST.

## Installation

Dateien mit unveränderten Pfaden in GitHub übernehmen und committen. Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_profile_password.sh
```

Bei Konflikten oder Fehlern stoppen und Ausgabe weitergeben. Kein Datenbankupgrade,
keine neuen Abhängigkeiten. Browser anschließend vollständig neu laden (Strg+F5).
Kein gespeichertes Passwort wird während der Installation verändert.

## Prüfung

Isolierte SQLite-Testdatenbank, keine Live-Nutzerkennwörter gelesen oder verändert.
`test_profile_password.py`: Login/CSRF/Kontotrennung, aktives Konto, falsches
Altpasswort, Länge, Wiederholung, gleicher Wert, keine geheimen HTML-/Auditwerte,
Hash nur des eigenen Kontos geändert, Remember-Cookie bereinigt, Abmeldung,
alte/neue Anmeldung, Rand-Leerzeichen und erhaltene persönliche Einstellungen.
Bestehende Profil- und Musterungsworkflowtests ebenfalls ausgeführt.
Node-DOM-Tests für drei Augensymbole, Beschriftung/aria-pressed, automatisches
Maskieren und unveränderte Feldwerte. Python-Kompilierung, Shell-/JS-Syntax,
Git-Diff und ZIP-Integrität geprüft. Kein echter Browser-/Mobilgerätetest;
fachfremde OpenCV-Erkennung wird nur in der Testumgebung gestubbt.
