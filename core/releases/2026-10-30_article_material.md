# Artikel: Rohstoff, Suche und Detailansicht

Basis: main c84dc3dcb14b05349aa58573c7bfa49873311914.
Vollständige Ersatzdateien für diese Erweiterung; kein kompletter Repository-Snapshot.

Artikel erhalten eine optionale material_id (ForeignKey materials.id, Index).
Bestehende Artikel bleiben ohne Rohstoffzuordnung erhalten. Kundenverknüpfung
und Werkzeuge bleiben unverändert. Upgrade ist wiederholbar und baut keine
vorhandenen Tabellen neu auf. Materialien mit zugeordneten Artikeln sind im
Löschdialog geschützt.

Kunde und Rohstoff können anhand der angezeigten Nummer/Bezeichnung gesucht
und geleert werden. Verwendet die bereits in FactoryOS eingebundene
TomSelect-Bibliothek; keine neue Paketabhängigkeit.

Neue responsiv gegliederte Artikelansicht und Formularformatierung.
Aktivitäten nur beim Artikel standardmäßig geschlossen (native details/summary,
auch per Tastatur bedienbar). Globale Aktivitätenansichten bleiben unverändert.

Prüfungen: Upgrade auf vereinfachter Bestandsstruktur zweimal durchgeführt,
Bestandsdatensatz erhalten. In isolierter SQLite-Testdatenbank: Zuordnen,
Entfernen, ungültige Material-ID, Formular-, Detail- und Listenrendering.
Die fremde Bildanalyse wurde beim Teststart ausgeklammert.
Produktive Raspberry-Datenbank ist nicht remote eingesehen.

Installation nach GitHub-Upload/Commit:

    cd /home/factoryos/FactoryOS
    git status --short
    git pull --ff-only origin main
    bash scripts/install_article_material.sh

Das Installationsskript prüft zuerst die Struktur, stoppt den Dienst,
sichert die Datenbank und führt das Upgrade aus. Bei Upgradefehler bleibt der
Dienst gestoppt; Fehlerausgabe weitergeben. Keine Neuinstallation erforderlich.
