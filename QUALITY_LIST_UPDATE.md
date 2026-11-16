# Prüfplan-Tabelle und Sichtprüfungs-Vorlagen

Basis: main 991d0bf; setzt das vorherige Prüfplan-Modul-Update voraus.
Enthalten sind vollständige neue/geänderte Dateien. Keine Migration und keine
Änderung vorhandener Prüfpläne, Freigaben oder Rollenrechte.

Dateien mit Verzeichnisstruktur nach GitHub übernehmen, dann:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_quality_list.sh
```

Danach die Seite vollständig neu laden, damit auch neue JavaScript-Dateien
geladen werden. Der Installer prüft die Voraussetzungen und startet den Dienst
neu. Er verändert die Datenbank nicht.

Die Übersicht ist wieder eine FactoryOS-Tabelle: Werkzeugnummer, Artikelnummer,
Bezeichnung, Revision, Status, Modulanzahl, Erstellzeit und Aktionen. Sie zeigt
die neueste Revision je Prüfplan. Artikelnummer und Prüfplan sind verlinkt.
Suche, Sortierung und Seitenwechsel verwenden die bestehende Tabellenfunktion.
Die Suche findet Werkzeug, Artikel, Bezeichnung, Revision und deutschen Status,
auch wenn entsprechende Spalten ausgeblendet sind. Die Spaltenauswahl wird
getrennt nach Benutzerkonto für diesen Browser-Tab gehalten, nicht im Konto
geräteübergreifend gespeichert. Werkzeugnummer und Aktionen bleiben sichtbar.

Im neuen Merkmal einer Sichtprüfung können typische Fehler vorausgewählt
werden: Grat, Luftschlieren, Brenner, Dieseleffekt, Einfallstellen, Bindenähte,
Silberschlieren, unvollständige Füllung, schwarze Punkte/Fremdpartikel,
Farbabweichungen, Fließlinien, Verzug, Risse sowie Kratzer/Druckstellen.
„Vorlage in Eingabefelder übernehmen“ füllt nur Merkmal, Kriterium und Methode.
Bereits ausgefüllte Felder werden nur nach Bestätigung ersetzt. Alle Angaben
bleiben manuell änderbar. Erst das ausdrückliche Hinzufügen speichert.
Es entstehen keine automatischen Freigaben, Messwerte oder Toleranzgrenzen.
Prüfflächen, Beleuchtung und Grenzmuster-/Zeichnungsbezug produktbezogen prüfen.
Ohne JavaScript bleibt die manuelle Eingabe verfügbar.

Lokale Tests: bisheriger vollständiger Prüfplan-Test, neue Listen-/Vorlagen-
Regression mit 25 Prüfplänen und JavaScript-Test für Übernahme/Abbruch.
Die echte Darstellung auf eurem Android-Gerät bitte nach Installation prüfen.
DuckDNS, Timeline, Maschinenbedienung und OCR bleiben unverändert.
