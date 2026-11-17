# PDF-Layout: Fehler-Oberbegriff zuerst

Ergänzung zum installierten PDF-Export. Vollständige Dateien mit Ordnerstruktur nach GitHub übernehmen, danach:

```bash
cd /home/factoryos/FactoryOS && git pull --ff-only origin main && sudo systemctl restart factoryos.service
```

Keine Datenbankmigration und kein Reset erforderlich. Neue PDFs bitte erneut aus der App exportieren; bereits heruntergeladene PDFs ändern sich nicht.

Der dunkle Kopfstreifen einschließlich sichtbarem FactoryOS-Schriftzug entfällt auf allen Seiten. Unter „FEHLERBILD #…“ steht groß die Fehlerkategorie statt der Kurzbeschreibung. Die Kategorie „Farbabweichungen / Farbschlieren“ erscheint als Oberbegriff **Farbabweichung**; die ursprüngliche Kategorie bleibt unverändert in den Stammdaten und in der Informationszeile „Fehlerart“ erhalten. Andere Kategorien werden unverändert als Überschrift verwendet.

Unter „Beobachteter Fehler“ steht zuerst die bisherige Kurzbeschreibung, zum Beispiel **Nicht richtig durchgefärbt**, danach die ausführliche Beschreibung. Abhilfe, Fotos, Artikel-/Werkzeugangaben und die Fußzeile mit Exportzeit/Seitenzahl bleiben enthalten. Es werden ausschließlich Darstellung und Reihenfolge im PDF verändert, keine gespeicherten Fehlertexte umgeschrieben. Einzel- und Katalogexport verwenden dasselbe Layout.

Automatisierter Text-/Reihenfolgetest und visuelle Prüfung mit künstlichem Beispielbild sowie einem langen mehrseitigen Dokument. Bestehende Einträge und Fotos bleiben erhalten.
