# Rechteverwaltung: Korrektur und ergänzende Prüfung

Basis main c88d664. ZIP enthält vollständige geänderte/neue Dateien mit ihren
Repository-Pfaden, Tests und Installationsskript. Keine Live-Datenbank enthalten.

## Bestätigte Fehler und Korrekturen

1. Benutzerverwaltung prüfte nur die Anmeldung. Produktionsnutzer konnten neue
   Admin-Konten anlegen, andere Konten ändern und sich selbst hochstufen.
   Jetzt serverseitig getrennte `users.view/create/edit/delete`-Kontrolle.
2. Mehrere Rollen-/Rechterouten waren nur mit login_required geschützt. Jetzt
   ausschließlich aktive Systemadministratoren. Die alternative Rollen-Rechteroute
   leitet lesend zur Matrix; schreibender Altpfad ist gesperrt. Der fehlerhafte
   Benutzer-Anlegepfad per POST auf die Benutzerliste ist ebenfalls gesperrt.
3. Fehlende Rechteprüfungen in Werkzeugen, Artikeln, Kunden, Aufträgen, Musterungen,
   Produktion/Projekten und QS. Zentrale Zugriffspolitik umfasst alle aktuell
   registrierten Endpunkte. Unbekannte neue Endpunkte sind standardmäßig gesperrt,
   bis eine ausdrückliche Zuordnung ergänzt wurde. Bestehende Material-/Maschinen-
   und Tool-Error-Rechte werden übernommen. Lese-/Schreib-/Exportrechte getrennt.
4. `has_permission` ignorierte deaktivierte Rollen; Adminbehandlung war gegenüber
   role_required uneinheitlich. Aktive Systemrolle `admin` besitzt jetzt ausdrücklich
   geschützten Vollzugriff; deaktivierte Rollen/Benutzer bekommen keinen Fachzugriff.
   Fehlende Rechte liefern HTTP 403 statt Referrer-Weiterleitungsschleifen.
5. Nichtadministrative delegierte Benutzerverwaltung kann keine weitergehenden
   Rollen vergeben und keine höher privilegierten oder administrativen Konten ändern.
   Auch eine Passwortzurücksetzung darf nicht zur Übernahme solcher Konten dienen.
   Rollen-/Rechteverwaltung selbst wird nie delegiert.
6. Eigene Konten dürfen nicht über die Administration gelöscht, deaktiviert oder
   umgestuft werden. Eigenes Passwort nur im Profil ändern. Systemrolle admin darf
   nicht umbenannt/deaktiviert/gelöscht werden. Verwendete Rollen nicht löschbar.
   Benutzer mit bekannten Vorgangsreferenzen sollen deaktiviert statt gelöscht werden.
7. CSRF-Schutz für administrative Schreibaufrufe und alle unten genannten
   bisher durch GET mutierenden Aktionen. Benutzer-/Rollenformulare enthalten Token.
8. Rechte-Matrix prüft eine Revision vor dem Speichern, damit veraltete Fenster keine
   zwischenzeitlich geänderten Rollenrechte überschreiben. Unbekannte Rechte-IDs werden
   zurückgewiesen. Rechteänderungen werden ohne Kennwörter/Hashes protokolliert.
9. Löschlinks für Artikel/Werkzeuge/Aufträge, Hauptbild-Auswahl sowie Tool-Error-
   Workflowlinks (Prüfung, Zurückgeben, Freigeben, Schließen, Revision) zeigen per GET
   jetzt nur eine Bestätigungsseite. Ausführung erst per POST mit CSRF-Token.
10. Hardcodierte QM-Rollenprüfung beim Anlegen eines Prüfplans durch `quality.inspect`
    ersetzt. Die zugewiesene Berechtigung ist maßgeblich, nicht eine abweichende
    Schreibweise des Rollennamens.
11. Sidebar, Start-/Stammdaten-/Admin-Dashboard und Benutzeraktionen berücksichtigen
    Rechte. Nicht alle fachlichen Detailbuttons wurden optisch ausgeblendet; auch
    dort erzwingt der Server die Berechtigung unabhängig von sichtbaren Links.
12. Hochgeladene Dateien unter Flask-Static und `/storage` benötigen Anmeldung und
    das zugeordnete Leserecht. Unbekannte Ablagebereiche sind vorsorglich admin-only.
13. Kritisch: Der bisher fest im Quellcode stehende Sitzungsschlüssel wurde entfernt.
    Neuer privater, zufälliger Schlüssel in `instance/session_secret.key` (0600,
    von Git ignoriert); alternativ ausdrücklich konfigurierte Umgebungsvariable
    `FACTORYOS_SECRET_KEY` oder Datei `FACTORYOS_SECRET_KEY_FILE`. Kein öffentlicher
    Fallback mehr. Vorhandene private Schlüssel werden nicht überschrieben.
    Ohne privaten Schlüssel startet die App nicht. Der Installer legt ihn an.
    Dadurch werden alle alten Sitzungen beim ersten Neustart ungültig. Jeder
    muss sich einmal neu anmelden. Daten/Passwörter/Profile werden nicht gelöscht.

## Rollenverhalten und Rechtekatalog

Die geschützte Systemrolle heißt `admin` (Groß-/Kleinschreibung normalisiert).
Vollzugriff wird in der Matrix erkennbar als fest angezeigt, nicht versehentlich
weggeklickt. Das Upgrade verlangt eine eindeutige aktive Adminrolle mit mindestens
einem aktiven Administratorkonto; sonst Abbruch statt Aussperren.

Bestehende Rechtezuweisungen der Fachrollen bleiben unverändert. Fehlende
Berechtigungsnamen werden ergänzt, aber NICHT automatisch an Produktion/Qualität
oder andere Rollen vergeben. Neue Tabellen sind nicht nötig. Vorhandene, vielleicht
zu weit gehende Zuweisungen werden nicht eigenmächtig gelöscht: diese bitte bewusst
prüfen. Neue Rechte sind konservativ zunächst unzugewiesen.

Wichtige Bereiche:

| Bereich | Rechte |
| --- | --- |
| Benutzer | users.view / create / edit / delete |
| Artikel / Kunden / Aufträge | articles / customers / orders jeweils .view / .create / .edit / .delete |
| Werkzeuge | tools.view / create / edit / delete / documents / excel_import / excel_export |
| Produktion | production.view / start / stop / setup / events; Kalender weiterhin admin-only |
| Musterung | sampling.view / create / edit / release / pdf_export; Buchungsstopp production.stop |
| Qualität | quality.view / inspect / delete / pdf_export |
| Projekte | projects.view / create; Zeitbuchung production.start / stop |
| Aktivitätsprotokoll | activity.view |
| Materialien/Maschinen/Tool-Errors | Bereits definierte bereichsspezifische Rechte |

`.view` ist nicht automatisch in `.edit` enthalten. Für die Nutzung über Übersichten
entsprechend auch das Leserecht vergeben. Beispiel Produktion: production.view plus
die tatsächlich gewünschten Start-/Stopprechte; keine users.*-Rechte, sofern keine
bewusst delegierte Benutzerverwaltung gewünscht ist. Für QS-Musterungen passende
sampling.*-Rechte ausdrücklich wählen. Dies ist keine automatische Rollenempfehlung
für euren gesamten Betrieb.

## Installation und wichtige Nachkontrolle

1. ZIP-Pfade unverändert nach GitHub übernehmen und committen.
2. Raspberry:

```bash
cd /home/factoryos/FactoryOS
git status --short
git pull --ff-only origin main
bash scripts/install_access_control.sh
```

Bei Konflikten/Fehlern stoppen und Ausgabe weitergeben. Der Installer prüft Code,
legt den privaten Sitzungsschlüssel an, prüft den Adminzugang, stoppt den Dienst
und sichert `instance/factoryos.db` plus vorhandene
WAL/SHM-Dateien nach `/home/factoryos/backups/access_control_<Zeitstempel>`. Dann wird
der Rechtekatalog ergänzt und FactoryOS neu gestartet. Bei Upgradefehler bleibt
der Dienst gestoppt. Das Upgrade ist wiederholbar; keine neuen Abhängigkeiten.

3. Als Administrator anmelden, Rechte-Matrix öffnen, insbesondere neue .view- und
   Musterungsrechte für die benötigten Fachrollen bewusst setzen. Matrix vollständig
   neu laden (Strg+F5); alte offene Formulare nicht weiterverwenden.
4. Mit dem konkreten Benutzer `user` in einem zweiten Browser testen: Administration
   ohne users.* nicht erreichbar; direkt aufgerufene Admin-URLs liefern 403. Eigene
   Profil-/Passwortfunktionen bleiben erreichbar. Bewusst erlaubte Produktion testen.
   Alle Nutzer müssen sich wegen des neuen Sitzungsschlüssels einmal neu anmelden.
   Der private Schlüssel gehört niemals in GitHub oder einen Chat. Falls statt der
   Standarddatei eine Umgebungsvariable verwendet wird, müssen Terminal und systemd
   dieselbe private Konfiguration erhalten.
5. Bestehende Benutzer und Rollen prüfen: Wegen der vorherigen Lücke könnten bereits
   ungewollte Konten oder Rollenzuweisungen existieren. Der Patch löscht/ändert solche
   Bestandsdaten nicht automatisch und kann nicht beweisen, ob die Lücke benutzt wurde.

Der neue Sitzungsschlüssel wird mit 0600-Dateirechten angelegt und wiederverwendet;
ein mit abweichendem Schlüssel signiertes Cookie wurde im Test als Anmeldung
zurückgewiesen. Die Testumgebung nutzt ausschließlich zufällige eigene Testschlüssel.

## Verifikation und Grenzen der Prüfung

`scripts/test_access_control.py`: synthetische SQLite-In-Memory-Datenbank,
187 verweigerte registrierte Endpunkt-/Methodenkombinationen, blockierte
Admin-Kontoanlage/Selbsterhöhung/Rollenrechteänderung, erlaubte explizite Rechte,
deaktivierte Benutzer/Rollen, Delegierungsgrenzen, Matrix-CSRF/Revision/Unbekannte IDs,
erfolgreiche Matrixänderung, Adminschutz, Bestätigungs-GET ohne Löschung und geschütztes
POST, Dateileseschutz und zweimaliges Upgrade. Neue unklassifizierte Route gesperrt.
Weitere Regressionen: bestehende Musterungsworkflows, Masterbatch, PDF-Erzeugung,
Benutzerprofil, Passwortwechsel, Artikelansicht und Node-UI-Tests. Die generelle
Workflow-Testfigur hat nun explizit eine Adminrolle; separate Rechte-Tests nutzen
absichtlich unprivilegierte Konten. Syntax, Shell und Diff/ZIP geprüft.
Fachfremde OpenCV-Erkennung nur in Tests gestubbt. Keine Raspberry-Live-Datenbank
geprüft oder geändert, kein vollständiger Penetrations-/Browser-/Deploymentscan.

Offene Punkte außerhalb dieses gezielten Rechtepatches:

- Falls Nginx/Apache hochgeladene Dateien direkt ausliefert, wird Flask umgangen.
  Diese Serverkonfiguration konnte nicht geprüft werden und muss gegebenenfalls
  separat angepasst werden. Dateischutz im Python-Code allein schützt keinen
  unabhängig freigegebenen Webserver-Ordner.
- Ein flächendeckender CSRF-Umbau sämtlicher fachlicher Formulare/AJAX-Aufrufe ist
  nicht enthalten. Dieser Patch schützt Adminmutationen und die zuvor unsicheren
  GET-Aktionen; Profil/Musterung besitzen zusätzlich ihre bisherigen Tokenprüfungen.
- Keine zusätzliche Zeilen-/Mandanten-/Maschinenbesitz-Rechtematrix. Bestehende
  fachliche Eigentümer-/Workflowprüfungen bleiben bestehen.
- Kein neues Login-Rate-Limit und keine automatische Sperrung aller fremden
  Sitzungen bei Passwortänderungen. Keine rückwirkende Wiederherstellung nicht
  protokollierter früherer Änderungen.
