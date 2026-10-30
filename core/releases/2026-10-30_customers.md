# Kundenstammdaten und optionale Artikelzuordnung

Basis: GitHub main c1433f559cf167a70256eddc9c0f6dd5f14e9cc9.
Vollständige Ersatzdateien; kein vollständiger Repository-Snapshot.

Neue Tabelle customers mit eindeutiger Kundennummer, Name, Kontaktdaten,
Anschrift, Notizen und Aktivstatus. Artikel erhalten eine nullable
customer_id mit Fremdschlüssel auf customers.id und einem Index.
Bestehende Artikel erhalten NULL; Artikel-Werkzeug-Beziehungen bleiben erhalten.
Keine Kaskadenlöschung von Artikeln. Zugeordnete Kunden sind über die
Anwendung gegen Löschung geschützt. Kundenauswahl kann entfernt werden.
Kundenrouten sind wie die bisherigen Artikelrouten für angemeldete Nutzer
zugänglich. Keine neue rollenbasierte Beschränkung wird eingeführt.

Kundenübersicht, Anlage, Bearbeitung und Detailseite sind über Stammdaten
erreichbar. Kundenzuordnung erscheint in Artikelliste, Formular und Detail.
Änderungen werden im vorhandenen ChangeLog gespeichert.
Der bestehende Feldnamenfehler tools/tool_ids beim Artikelanlegen wurde korrigiert.

Die Migrationen im Repository bilden den aktuellen Betriebsstand nicht
vollständig ab (Kalender und Materialien nutzen ebenfalls Upgrade-Skripte).
Darum kein pauschales flask db upgrade. Das beiliegende Upgrade kontrolliert
die tatsächliche SQLite-Struktur und ergänzt ausschließlich Tabelle/Spalte/Index.
Die reale Raspberry-Datenbank wurde nicht aus der Ferne eingesehen.

Nach Upload der ZIP-Inhalte mit erhaltenen Pfaden und GitHub-Commit:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_customer_masterdata.sh

Bei lokalen Konflikten nicht überschreiben. Ausgabe weitergeben.
Installationsskript erkennt übliche Python-Umgebungen, prüft die Struktur,
stoppt den Dienst, sichert instance/factoryos.db und führt das Upgrade aus.
Bei Upgradefehler bleibt der Dienst bewusst gestoppt.
Upgrade ist wiederholbar. Tabellen werden nicht neu aufgebaut oder gelöscht.
