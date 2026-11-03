# Korrektur: installierte Texterkennung im FactoryOS-Dienst finden

Basis: main 18c3960. Der bisherige Code verwendete ausschließlich
shutil.which('tesseract'). Ein auf das Python-venv begrenzter Dienst-PATH kann
dadurch „Lokale Texterkennung fehlt“ melden, obwohl Tesseract im interaktiven
Terminal funktioniert. Der Screenshot belegt die Meldung und die erfolgreiche
Terminalinstallation; die tatsächliche entfernte Dienstumgebung wurde nicht
ausgelesen. Der PATH-Unterschied ist die naheliegende, hier abgesicherte Ursache.

Änderungen:

- Suche zusätzlich in /usr/bin/tesseract, /usr/local/bin/tesseract und /bin/tesseract.
- Aufruf immer direkt mit ermitteltem Programmpfad, ohne Shell.
- Optionaler absoluter Admin-Pfad über FACTORYOS_TESSERACT_CMD oder Flask-Konfiguration
  TESSERACT_CMD; ungültige Vorgaben werden nicht still ignoriert.
- Diagnose mit derselben Python-Umgebung und absichtlich eingeschränktem PATH.
- Keine Änderung von systemd-Rechten/Sandbox, keine erneute Paketinstallation,
  keine Datenbankänderung und keine APK-Änderung.

Dateien in GitHub übernehmen, dann auf dem Raspberry:

```bash
cd /home/factoryos/FactoryOS
git pull --ff-only origin main
bash scripts/install_material_scan_path_fix.sh
```

Installer prüft OCR normal und mit eingeschränktem Suchpfad und startet den
Dienst neu. Danach Foto erneut auslesen. Bei Fehlern die Ausgabe weitergeben.
Eine zusätzliche systemd-Sandbox/Dateisystemsperre wird nicht umgangen; falls
der Dienst trotz funktionierender Diagnose keinen Zugriff hat, dessen explizite
Schutzkonfiguration als nächsten Schritt prüfen. Keine Umgebungsvariablen oder
Zugangsdaten vollständig ausgeben.

Geprüft: echter lokaler Tesseract-Aufruf mit eingeschränktem PATH sowie bestehende
OCR-Integration auf synthetischem Etikett. Kein Zugriff auf produktiven Raspberry,
keine Untersuchung der konkreten entfernten Dienstumgebung.
