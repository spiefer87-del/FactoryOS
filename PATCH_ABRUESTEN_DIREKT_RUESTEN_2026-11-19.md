# Abrüsten abschließen: direkt rüsten oder ohne Werkzeug frei stehen lassen

GitHub-Basis: spiefer87-del/FactoryOS, main,
Commit 9d2dbc547a405e43c1b1a3842543e4775f36919d.

Das ZIP enthält vollständige geänderte und neue Dateien mit Repository-Pfaden,
keinen einzelnen Diff. ZIP entpacken, Dateien mit Ordnerstruktur in das
Stammverzeichnis des GitHub-Repositorys übernehmen und committen.
Keine neue Datenbanktabelle, keine Migration und keine neuen Rollenrechte nötig.

## Neuer Ablauf

„Abrüsten abschließen“ öffnet jetzt eine eigene Auswahlseite:

1. **Abrüsten abschließen und direkt rüsten**
   - Optional den Folgeauftrag auswählen. Der nächste Planauftrag wird, wenn
     vorhanden, vorausgewählt; sein Werkzeug wird als Vorschlag angeboten.
   - Die nächste Werkzeugnummer aus den Stammdaten auswählen bzw. eingeben
     und die konkrete Nummer mit „Werkzeug geprüft“ bestätigen.
   - Mit dem Button wird der alte Abrüstvorgang abgeschlossen und der neue
     Rüstvorgang begonnen. Beide Grenzen erhalten exakt denselben Zeitpunkt.
     Es entsteht keine zusätzliche Frei-Buchung zwischen den beiden Vorgängen.
   - Der neue Zustand lautet „Rüsten läuft“. Das nächste Werkzeug ist noch
     nicht fertig gerüstet und es wird keine Produktion gestartet.
2. **Ohne Werkzeug frei stehen lassen**
   - Der Abrüstvorgang endet, der bestätigte Werkzeugbestand wird leer.
   - Die freie Zeit ohne Werkzeug beginnt. Es entsteht kein neuer Rüstvorgang.
   - Angaben im Bereich „nächstes Werkzeug“ werden für diese Auswahl ignoriert.

Ohne JavaScript können Auftragsvorschlag und eigene Werkzeugwahl über die
Ladebuttons übernommen und anschließend bestätigt werden. Die serverseitigen
Prüfungen bleiben maßgeblich. Auch der frühere POST-Button für das Abrüstende
führt im Webablauf zunächst zur neuen Auswahlseite.

## Zeiten, Werkzeugbindung und Protokoll

- Abrüstbuchung und Abrüstnachweis bleiben dem alten Werkzeug zugeordnet.
  Die neue Rüstbuchung und der neue Rüstnachweis gehören zum ausgewählten
  nächsten Werkzeug und gegebenenfalls zum Folgeauftrag.
- Beide Übergänge werden in einer gemeinsamen Transaktion gespeichert. Bei
  einem Fehler werden Abrüstende und neuer Rüstbeginn gemeinsam zurückgerollt.
- Unbekannte Werkzeuge, widersprüchliche Auftragszuordnungen, fremde Maschinen-
  reservierungen und bereits anderweitig montierte oder im Rüsten gebundene
  Werkzeuge werden abgefangen. Stale bzw. konkurrierende Befehle können keinen
  zweiten Folgevorgang erzeugen. Identische Wiederholungen sind idempotent.
- Das bisherige Rüstrecht production.setup sowie production.view sind nötig.
  Ein zusätzliches Produktionsstartrecht ist für den Beginn des Rüstens nicht
  erforderlich; der spätere tatsächliche Produktionsstart bleibt separat geschützt.
- Bei inaktiver Maschine ist ein neuer Rüstbeginn gesperrt. Das tatsächliche
  Abrüstende kann trotzdem als leerer Maschinenzustand bestätigt werden.
- Zugeordnete Musterungen müssen wie beim bisherigen Rüstbeginn vorbereitet
  und dieser Maschine zugeordnet sein. Eine Prüf- oder Produktionsfreigabe
  wird nicht automatisch erteilt. Rüsten nur mit Werkzeug, ohne Auftrag, bleibt
  möglich. Der Planauftrag wird erst beim späteren Produktionsstart als
  gestartet übernommen, nicht bereits beim Rüstbeginn.
- Die Entscheidung sowie altes und nächstes Werkzeug werden lesbar in den
  Aktivitäten protokolliert. Die Zeitwertung trennt Abrüsten und Rüsten wie
  bisher; bei direkter Übergabe gibt es keine freie Zeit dazwischen.

Bereits vorhandene Buchungen, beispielsweise die Einträge 24/25/26 aus dem
Screenshot, werden nicht nachträglich gelöscht oder zeitlich umgeschrieben.
Der neue Ablauf verhindert solche Zwischenbuchungen künftig. Wird dagegen
bewusst „frei stehen lassen“ gewählt und erst später separat gerüstet, bleibt
die tatsächlich gebuchte freie Zeit erhalten. Bestehende Korrekturabläufe sind
für eine belegte historische Zeitkorrektur weiterhin verfügbar.

## Raspberry Pi

Nach Upload und Commit auf GitHub:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos
sudo systemctl status factoryos --no-pager
sudo journalctl -u factoryos -n 80 --no-pager
```

Danach die Maschinenbedienung bzw. den geöffneten Dialog neu laden.

## Prüfung

Erfolgreich mit isolierten SQLite-Testdatenbanken geprüft:

```bash
python scripts/test_teardown_next_setup.py
python scripts/test_teardown_next_setup_concurrency.py
python scripts/test_machine_control.py
python scripts/test_tool_mount.py
python scripts/test_setup_wait.py
python scripts/test_setup_wait_concurrency.py
python scripts/test_initial_idle.py
python scripts/test_order_completion.py
python scripts/test_order_planning.py
python scripts/test_planning_chain.py
python scripts/test_quantity_edit_navigation.py
python scripts/test_timeline_ranges.py
python scripts/test_permission_labels.py
python scripts/test_activity_review.py
node scripts/test_machine_control_selection.cjs
```

Die neuen Tests prüfen die exakte Abrüst-/Rüstgrenze ohne Frei-Buchung,
getrennte Werkzeug- und Rüstnachweise, einen echten leeren Maschinenzustand,
beibehaltene Warteschlange, manuelle und musterungsbezogene Rüstzuordnungen,
konkrete Werkzeugbestätigung, HTTP-/No-JS-Ablauf, Rechte und CSRF, ungültige
Stammdaten und Zuordnungen, inaktive Maschinen, unveränderte Historie und
Rollback auch nach spätem Werkzeug- oder Auditfehler. Mit unabhängigen
Datenbanksitzungen wurden doppelte Übermittlung, konkurrierende Auswahl
„Rüsten/Frei“ und die gleichzeitige Reservierung desselben nächsten Werkzeugs
durch zwei Maschinen geprüft: genau ein erfolgreicher Vorgang, kein Deadlock.

HTML und Formularabläufe sind geprüft. Ein grafischer Android-Browsertest war
in dieser Umgebung nicht möglich.
