# Maschinenbedienung: verbindlicher Integrationsrahmen für spätere Controller

Stand: 02.11.2026. Diese Version bucht manuell in FactoryOS; sie sendet keine
elektrischen Befehle an Maschinen. Der Touchscreen kann bereits die eigenständige,
anmeldepflichtige Bedienseite verwenden. Ein Geräte-API, Gerätezugangsdaten,
Hardwareansteuerung oder automatische Maschinensignale sind NICHT freigeschaltet.

## Gemeinsamer Befehlskern

Alle Maschinenzustandsänderungen laufen über
`factoryos.modules.production.services.machine_control_service.execute`.
Der Server ist führend. Ein zukünftiger Adapter darf `TimeBooking` nicht direkt
schreiben und nicht den Zustand eines Geräts ungeprüft als Wahrheit übernehmen.

Parameter:

- `machine_id`: am Server aus einer geprüften Gerätebindung bestimmen.
- `user_id`: angemeldeten Bediener serverseitig bestimmen; niemals aus beliebigem
  JSON übernehmen. Persönliche Rollenrechte bleiben auch am Touchscreen wirksam.
- `action`: ausschließlich Schlüssel aus `ACTIONS`, keine freien Prozesscodes.
- `command_id`: kanonische UUID; für einen Wiederholungsversuch exakt gleich lassen.
- `expected_revision`: zuvor gelesenen Serverstand mitgeben; keine automatischen
  Wiederholungen mit einer frisch beschafften Revision nach einem Konflikt.
- Optional Auftrags-ID, Werkzeug, aktiver Störgrund und Kommentar.

Ein identischer Befehl desselben Bedieners für dieselbe Maschine mit identischem
Inhalt liefert den vorhandenen Beleg zurück. Wiederverwendete UUID mit geändertem
Inhalt wird abgewiesen. Vor Replay werden die aktuellen Rechte erneut geprüft.

Der Adapter benötigt vor Freigabe eigene TLS-/Geräteauthentifizierung, widerrufbare
Maschinenbindung, Bedieneranmeldung, Zugriffsbegrenzung und Protokollierung der
Geräteherkunft. Das bestehende `source`-Feld verwendet zurzeit ausschließlich
`app`; ein Geräteadapter muss vertrauenswürdige Provenienz ergänzen. Keine Token
oder Passwörter im Browsercode, keine pauschale Admin-Identität für Geräte.

## Zustandsregeln

| Zustand | Verfügbare Folgeschritte |
| --- | --- |
| Frei | Auftrag starten, Rüsten, Abrüsten, Wartung, Sonstiges, Störung |
| Produktion / Musterung | Pause, Störung, Stoppen |
| Rüsten / Abrüsten | Beenden, Störung, Stoppen |
| Wartung / Sonstiges | Beenden, Störung, Stoppen |
| Störung | Entstören mit Behebungsbeschreibung |
| Pause / bereit | Vorherigen Vorgang ausdrücklich fortsetzen, Störung, Stoppen |

Entstören führt bei gespeichertem Vorgang zu PAUSE, sonst zu FREI. Es startet
NIEMALS automatisch Produktion oder einen anderen Vorgang. Bei Störung während
einer Pause bleibt der zuvor unterbrochene Vorgang erhalten. Eine Unterbrechung
reserviert den Auftrag weiterhin an dieser Maschine. Stoppen gibt die Reservierung
frei, schließt den Auftrag aber nicht als erfolgreich/fertig ab. Rüsten beenden
führt zu FREI; der Produktionsstart ist ein eigener Befehl mit Auftragsauswahl.
Ein Störgrund allein bestätigt keine technische Sicherheit oder QS-Freigabe.

## Transaktionen und Konflikte

Eine gemeinsame Datenbanksperre serialisiert Maschinenbefehle einschließlich
maschinenübergreifender Auftragsreservierung. Alte Buchung schließen, neue öffnen,
Fortsetzungskontext, Versionszähler, Befehlsbeleg und Änderungsprotokoll werden in
einer Transaktion gespeichert. Bei Fehlern muss der Aufrufer immer rollback ausführen.
Das verhindert Teilbuchungen. Der aktuelle Ansatz ist bewusst einfach für den
manuellen Betrieb; vor hochfrequenten SPS-Signalen Durchsatz, Aufbewahrung und
entkoppelte Signalerfassung gesondert auslegen.

Mehrere aktive Altbuchungen sperren Befehle. Kein automatisches Schließen,
Zurückdatieren oder Reparieren widersprüchlicher Daten. Neue Vorgänge auf inaktiven
Maschinen sind gesperrt. Fertige/gesperrte Aufträge und nicht freigegebene Musterungen
können nicht gestartet/fortgesetzt werden. Ein gültiger Sollzyklus ist erforderlich.

## Verbindung und Offline-Betrieb

Die App fragt im geöffneten Bedienfeld alle 15 Sekunden die Revision ab.
Bei geändertem Stand, abgelaufener Anmeldung oder Verbindungsfehler werden
Schaltflächen gesperrt und eine erneute Prüfung verlangt. Der Server prüft bei
jedem Befehl unabhängig davon den tatsächlichen Stand. Keine Offline-Warteschlange,
kein automatischer Start nach Wiederverbindung, kein automatisches Entstören.
Nach Netzwerkabbruch zunächst aktuellen Zustand lesen; einen unklar quittierten
Befehl nur mit seiner ursprünglichen UUID und unverändertem Inhalt erneut prüfen.

## Sicherheit und spätere Inbetriebnahme

Diese Software ist keine sicherheitsgerichtete Maschinensteuerung und ersetzt
weder Not-Halt, Schutztürüberwachung noch technische Freigaben. Vor einer echten
Hardwareverbindung sind Risikobeurteilung, Zuständigkeiten, Maschinenhersteller-
Schnittstellen, Signalquittierung, Uhrenabgleich und Ausfallverhalten separat zu
planen und an einer Testanlage abzunehmen. FactoryOS darf diese Schutzfunktionen
nicht umgehen. Physische Maschinenzustände sind bis dahin unbekannt, nicht simuliert
gemessen. Die manuelle Historie ist eine Bedienerangabe.
