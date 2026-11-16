# Prüfplan: Module und einheitlicher Statuskopf

Basis: FactoryOS main, Stand 84a6b07. Dieses Paket enthält vollständige neue und
geänderte Dateien mit ihren Verzeichnissen, nicht nur einen Diff.

## Installation

Dateien mit gleicher Ordnerstruktur ins GitHub-Repository übernehmen. Danach
auf dem Raspberry Pi eine Zeile ausführen:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_quality_plan.sh
```

Der Installer prüft die Struktur, stoppt den Dienst, sichert die bestehende
SQLite-Datenbank einschließlich vorhandener WAL-Dateien, ergänzt die neuen
Felder/Tabellen und startet den Dienst wieder. Bei einem Fehler bleibt der
Dienst zur Prüfung gestoppt. Keine Bestandsdatenbank ersetzen oder einspielen.
Die Datenbankänderung ist additiv und wiederholbar. Vorhandene Prüfpläne,
Freigaben, Bilder, Rollen und Rechte werden nicht umgeschrieben.

## Bedienung

- Gemeinsamer Statuskopf wie bei Fehlermeldungen: Revision, Aktuell/Historisch,
  Entwurf → In Prüfung → Freigegeben → Geschlossen und Revisionshistorie.
- Ausgearbeitete Module: Identifizierung mit Referenzbildern, Maßprüfung mit
  Zeichnungsmarkern und manueller Eingabe, Lehrenprüfung mit Prüfmittelstamm,
  Sichtprüfung, Textprüfung/Hinweise, Gewicht, Funktion, Material/Farbe,
  Verpackung/Kennzeichnung.
- Jedes Modul hat eine Bezeichnung, ein Prüfintervall/einen Anlass,
  Stichprobenumfang, Verantwortung und eine optionale Prüfanweisung.
- Prüfmerkmale enthalten Methode/Hilfsmittel und konkrete Annahme-/Fehlerkriterien.
  Gewicht hat zusätzlich Sollgewicht, Toleranz minus/plus und g/kg/mg.
- Module lassen sich verschieben und im Entwurf entfernen. Merkmale lassen
  sich bearbeiten; Referenzbilder und Zeichnungen bleiben verfügbar.
- Sichtbare Fehlerübersicht, Feldhinweise und erhaltene Eingaben bei ungültigen
  neuen Modul-/Merkmalformularen. Veraltete Formulare werden abgewiesen.
- Die Übersicht verwendet deutsche Statusbezeichnungen. Die Artikelnummer
  führt zum zugehörigen Artikel.

## Prüfung und Freigabe

Vor dem Senden zur Prüfung und vor der Freigabe werden vollständige Module
geprüft. Unvollständige Maße, fehlende Annahmekriterien oder inaktive/überfällige
Prüfmittel verhindern die Freigabe mit konkreten Hinweisen. Es werden keine
Toleranzen, Stichproben oder Qualitätsentscheidungen automatisch erfunden.

In Prüfung ist der Inhalt gesperrt; mit „Zur Bearbeitung zurückgeben“ wird
er wieder zum Entwurf. Freigegebene/geschlossene Fassungen werden nicht
nachträglich bearbeitet. Eine neue Entwurfsrevision kopiert Module, Bilder,
Maß-/Lehrenmerkmale und Prüfvorgaben. Frühere Freigaben bleiben in der Historie.
Auch alte Marker-, Upload- und Bearbeitungswege prüfen die Revisionssperre.

Bestehende Rechte bleiben maßgeblich: quality.view zum Lesen, quality.inspect
für Bearbeitung und Statuswechsel, quality.delete zum Entfernen,
quality.pdf_export für PDF. Es werden keine Rechte automatisch vergeben.

## PDF

Alle Module, Prüfumfang, Kriterien, Referenzbilder, Zeichnungsmarker und
Freigabeangaben sind enthalten. Der Dateiname lautet beispielsweise
COR248_Pruefplan_Rev_1.0.pdf. Entwürfe sind als solche gekennzeichnet. Der
Export verändert weder Inhalt noch Status. Ein Prüfplan ist eine Anweisung,
kein automatisch ausgefülltes Mess-/Ergebnisprotokoll.

## Prüfung des Updates

Lokale Tests: additive Migration zweimal, alle neun Module, Anlegen/Ändern/
Entfernen, erhaltene Eingaben und Feldfehler, Statuswechsel, Revisionskopie
einschließlich Bildern und Zeichnungsmaßen, Sperren alter Bearbeitungswege,
CSRF/veraltete Formulare, Leseberechtigung ohne Schreibrecht und vollständiger
PDF-Export. PDF-Seiten wurden gerendert und visuell geprüft. Bestehende
Berechtigungs- und Erstbestands-/Timeline-Regressionen wurden mitgetestet.
Ein Konkurrenztest mit unabhängigen SQLite-Sitzungen prüft, dass zwei
gleichzeitige Revisionsanforderungen nur eine einzige neue Revision erzeugen.

Die visuelle Browserprüfung der Handyansicht war in dieser Umgebung durch
die Browser-Ausführungsbeschränkung blockiert. Responsive Regeln sind
implementiert; die endgültige Darstellung auf eurem Android-Gerät bitte prüfen.
Keine Änderungen an DuckDNS, Tailscale, Maschinensteuerung oder OCR-Anbietern.
