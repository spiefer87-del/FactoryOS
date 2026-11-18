# Rüstende, gerüstete Wartezeit und Maschinenzeitauswertung

Basis: spiefer87-del/FactoryOS, main,
Commit 868c7e853f298530f0898de8ac7b0c8461bfca63.

Dieses ZIP enthält die vollständigen geänderten und neuen Dateien, mit ihren
Repository-Pfaden. Es ist kein einzelner Diff. ZIP entpacken, alle enthaltenen
Dateien mit Ordnerstruktur in das Stammverzeichnis des GitHub-Repositorys
übernehmen, bestehende Dateien ersetzen und committen.

## Installation auf dem Raspberry Pi

Dieser Patch ergänzt eine Tabelle für die eindeutige Einordnung der Leerlauf-
und Wartebuchungen. Deshalb bitte das Installationsskript verwenden, statt nur
den Dienst neu zu starten. Es prüft die Voraussetzungen, hält den Dienst an,
sichert die bestehende SQLite-Datenbank einschließlich vorhandener WAL/SHM-
Dateien unter /home/factoryos/backups/setup_wait_DATUM_UHRZEIT, ergänzt die neue
Tabelle und startet den Dienst wieder. Keine bestehenden Buchungen, Mengen,
Werkzeugbestände oder Rollenrechte werden durch die Migration verändert.

Nach Upload und Commit auf GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && bash scripts/install_setup_wait.sh
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Das Skript verwendet die vorhandene Python-Umgebung (.venv oder venv) und den
bereits in vorherigen Installationsskripten verwendeten Datenbankpfad
instance/factoryos.db. Bei einer fehlgeschlagenen Migration bleibt der Dienst
zur Prüfung gestoppt. Die Sicherung wird nicht automatisch zurückgespielt.
Danach die Maschinenbedienung, Timeline und Buchungsübersicht neu laden.

## Ablauf für die Testphase

### Rüsten abschließen

„Rüsten abschließen“ öffnet eine eigene Auswahlseite:

- **Rüsten abschließen und Produktion starten:** Auftrag auswählen bzw. den
  zugehörigen Rüstauftrag übernehmen und den tatsächlichen Produktionsbeginn
  sowie die nötigen Voraussetzungen/Freigaben ausdrücklich bestätigen.
  Rüstende und Produktionsbeginn erhalten exakt denselben Zeitpunkt. Es wird
  keine Frei-Buchung dazwischen erzeugt. Werkzeug, Musterungsstatus, Auftrags-
  reservierung und Planreihenfolge werden wie beim normalen Start geprüft.
- **Rüsten abschließen und warten:** Wartegrund auswählen. Der bekannte
  Auftragsbezug und das bestätigte montierte Werkzeug bleiben erhalten. Der
  Auftrag bleibt auf dieser Maschine reserviert und kann nicht gleichzeitig
  auf einer anderen Maschine gestartet werden. Das ist keine Produktionszeit.

Wartegründe: Material fehlt, Temperatur/Aufheizen, QS-Freigabe, Personal,
geplanter späterer Produktionsstart und Sonstiges. Bei Sonstiges sind mindestens
fünf Zeichen Erläuterung erforderlich. Rüsten ohne Auftragszuordnung bleibt
weiterhin möglich; ein fehlender Auftragsbezug wird nicht nachträglich erfunden.

Das Produktionsstartrecht wird zusätzlich zum Rüstrecht serverseitig geprüft.
Ein Benutzer mit Rüstrecht kann ohne Produktionsstartrecht das Rüsten mit
Wartegrund abschließen. Eine Musterung muss weiterhin im passenden Status und
dieser Maschine zugeordnet sein. Es wird keine Freigabe automatisch erteilt.
Abrüsten endet wie bisher mit der ausdrücklichen Bestätigung „ohne Werkzeug“.

### Während des Wartens

Die Maschinenbedienung zeigt „Gerüstet · wartet auf Produktionsstart“ mit
Werkzeug, bekanntem Auftrag und Wartegrund. Ab fünf Minuten ohne Produktion
erscheint ein Hinweis, auch bei bereits erfasstem Grund. Dieser Hinweis ist
eine Erinnerung, keine neue Pflicht zur wiederholten Begründung. Der bestehende
Statusabruf aktualisiert ihn ohne neue Buchung.

„Wartegrund erfassen / ändern“ dokumentiert den Grund ab jetzt als neuen
Zeitabschnitt. Frühere Abschnitte behalten ihren bisherigen Grund. Eine Änderung
des Grundes setzt die Erinnerung bei ununterbrochener gerüsteter Wartezeit nicht
zurück. Der Produktionsstart erfolgt weiterhin bewusst über die Bedienung.

Ein ausdrücklicher Wartegrund mit unbekanntem Ende wird in der Planung als
offene Startvoraussetzung behandelt. Bei Bedarf kann eine zukünftige
Verfügbarkeit mit Begründung geschätzt werden. Beim bereits fertig gerüsteten,
zugeordneten Auftrag wird dann keine zweite Rüstzeit angesetzt.

## Darstellung und Auswertung

- Die Buchungsübersicht zeigt statt „FREI · START“ den belegten Zustand:
  abgerüstet ohne Werkzeug, gerüstet ohne Produktion bzw. wartet auf Start,
  oder ausdrücklich ungeklärter Werkzeugzustand. Werkzeug und Wartegrund
  stehen in eigenen Feldern. Auf dem Handy erscheinen die Zeilen als Karten.
- Die Zeitauswertung trennt Abrüsten, Rüsten, gerüstetes Warten, abgerüsteten
  Leerlauf, ungeklärten Leerlauf, Produktion, Musterung und weitere Tätigkeiten.
  Gerüstete Wartezeit wird zusätzlich nach Grund aufgeschlüsselt.
- Suche, Datumsgrenzen in Europe/Berlin und Zeitbasis filtern die Auswertung.
  Standard ist der Arbeitskalender; alternativ kann die gesamte gebuchte
  Kalenderdauer einschließlich arbeitsfreier Zeiten angezeigt werden. Summen
  gelten für alle Treffer, nicht nur die sichtbare Tabellenseite. Randintervalle
  werden am Zeitraum abgeschnitten, aktive Buchungen bis zum Abruf gezählt.
- Überlappende Buchungen werden mit einem Hinweis kenntlich gemacht. Gleiche
  Zeitarten werden pro Maschine vereinigt; unterschiedliche überlappende Arten
  müssen vor verbindlicher Auswertung fachlich geklärt werden.
- Im Auftrag erscheint die eindeutig zugeordnete gerüstete Wartezeit separat.
  Sie erhöht weder die gebuchte Produktionszeit noch die Produktions-Sollabweichung.
- Timeline und Maschinenbedienung zeigen gerüstetes Warten als eigenen Zustand.
  Normale Wartezeiten sind farblich von roten Produktionsüberschreitungen getrennt.

## Historie und bestehende Korrekturen

Für neue Leerlaufintervalle werden die damalige Werkzeugbestätigung und der
Wartegrund als eigener Nachweis gespeichert. Der technische FREI-Prozess bleibt
zur Kompatibilität mit vorhandenen Buchungsabläufen erhalten; seine Bedeutung
wird aus diesem Nachweis gelesen.

Vorhandene Buchungen bleiben unverändert. Die Darstellung alter Frei-Intervalle
nutzt ausschließlich die damaligen Befehlsprotokolle, nicht den heutigen
Werkzeugbestand. Widersprüchliche oder fehlende Nachweise bleiben ungeklärt;
fehlende alte Wartegründe bleiben „Nicht erfasst“. Auftragslose historische
Zeiten werden nicht einem späteren Auftrag zugeschlagen.

Wird ein Werkzeugbestand während einer Frei-Phase korrigiert, beginnt ein neuer
Zeitabschnitt. Der alte Zustand wird nicht rückwirkend umbeschriftet. Start-/
Endzeitkorrektur, Buchungsprüfung und Administrator-Reparatur bleiben nutzbar.
Bei erlaubter Löschung wird der zugehörige Leerlaufnachweis mit entfernt und
zuvor im Änderungsprotokoll erhalten. Unbekannte fachliche Verknüpfungen bleiben
weiterhin geschützt. Entscheidungen und Gründe erscheinen lesbar in den
Aktivitäten. Alte interne Aufrufer des Rüstendes bleiben kompatibel; ihr Grund
wird nicht nachträglich als bewusste neue Warteentscheidung ausgegeben.

## Geprüft

Mit isolierten SQLite-Testdatenbanken und synthetischen Daten geprüft:

```bash
python scripts/test_setup_wait.py
python scripts/test_setup_wait_concurrency.py
python scripts/test_machine_control.py
python scripts/test_tool_mount.py
python scripts/test_initial_idle.py
python scripts/test_booking_end_time.py
python scripts/test_order_statistics.py
python scripts/test_order_completion.py
python scripts/test_booking_review.py
python scripts/test_admin_booking_repair.py
python scripts/test_setup_booking_review.py
python scripts/test_activity_review.py
python scripts/test_runtime_overrun.py
python scripts/test_timeline_ranges.py
python scripts/test_order_planning.py
python scripts/test_planning_chain.py
python scripts/test_permission_labels.py
python scripts/test_ui_consistency.py
node scripts/test_machine_control_selection.cjs
```

Neue Prüfungen umfassen die Migration zweimal ohne Altbuchungs-/Rechteänderung,
atomaren Direktstart ohne Zwischenbuchung, doppelte Übermittlung und konkurrierende
Start-/Warteentscheidungen, Rollback bei spätem Fehler, Reservierungen und
Planverbrauch, Pflichtgründe und Rechte, Statusprüfung bei Musterungen, Erhalt
alter Wartegründe, Erinnerung nach fünf Minuten, Datums-/Kalendergrenzen,
getrennte Zeitwerte, historische Belege und ungeklärte Zustände, Lesezugriffe ohne
neue Buchungen/Mengen sowie beide bestehenden Löschwege mit erhaltenem Audit.
Syntaxprüfungen für Python und das Installationsskript sind enthalten.

HTML-Ausgabe und Formularabläufe wurden geprüft. Ein grafischer Android-
Browsertest war in dieser Umgebung nicht möglich; die Testphase auf euren
Endgeräten bleibt für die optische Kontrolle sinnvoll.
