"""Allowlisted dashboard destinations, filtered by current account permissions."""
from flask import current_app,url_for
from factoryos.models.user import User
from factoryos.extensions import db
from .access_control import allowed,policy

# key, group, title, icon, endpoint, description
CATALOG=(
 ('booking_journal','Produktion','Buchungsübersicht','🧾','booking_review.journal','Zeitbuchungen suchen, prüfen und reparieren'),
 ('defect_catalog','Qualität','Fehlerkatalog','📷','article_defects.overview','Produktionsfehler je Artikel mit Fotos'),
 ('complaints','Qualität','Reklamationen','📨','complaints.overview','Eigener Reklamationsbereich'),
 ('production','Hauptbereiche','Produktion','🏭','production.dashboard','Produktionsübersicht'),
 ('orders','Hauptbereiche','Aufträge','📋','orders.dashboard','Aufträge und Fertigungsdaten'),
 ('inventory','Hauptbereiche','Lager','🏬','inventory.dashboard','Bestände, Übergaben und Warenausgang'),
 ('quality','Hauptbereiche','Qualität','🔬','quality.dashboard','Qualitätsmanagement'),
 ('projects','Hauptbereiche','Projekte','📁','projects.dashboard','Projektübersicht'),
 ('masterdata','Hauptbereiche','Stammdaten','🗂','masterdata.dashboard','Stammdatenpflege'),
 ('tool_list','Stammdaten','Werkzeugliste','🛠','tools.list_tools','Direkt zur Werkzeugübersicht'),
 ('article_list','Stammdaten','Artikelliste','📦','articles.list','Direkt zur Artikelübersicht'),
 ('customers','Stammdaten','Kunden','👥','customers.overview','Kundenstammdaten'),
 ('machines','Stammdaten','Maschinen','🏭','machines.dashboard','Maschinenstammdaten'),
 ('materials','Stammdaten','Materialien','🧱','materials.dashboard','Rohstoffe und Farbbatches'),
 ('planning','Produktion','Auftragsplanung','▤','production.planning','Reihenfolge je Maschine planen'),
 ('booking','Produktion','Maschinen-Timeline','⏱','production.booking_dashboard','Maschinenzustände und Bedienung'),
 ('errors','Produktion','Fehlermeldungen','⚠','tool_error.dashboard','Werkzeugfehler und Maßnahmen'),
 ('inspection_plans','Qualität','Prüfpläne','📐','inspection.dashboard','Prüfpläne und Revisionen'),
 ('gauges','Qualität','Prüfmittel','🧪','quality_gauges.gauge_home','Prüfmittelverwaltung'),
 ('activity','Weitere Bereiche','Aktivitäten','📖','activity.list','Änderungsprotokoll'),
 ('admin','Weitere Bereiche','Administration','⚙','admin.dashboard','Administration entsprechend deinen Rechten'),
 ('profile','Weitere Bereiche','Mein Profil','👤','profile.settings','Persönliche Einstellungen'),
)
DEFAULT_TILES=['production','orders','inventory','quality','projects','masterdata','admin']

def permitted(user_id):
    user=db.session.get(User,user_id)
    if not user:return []
    return [dict(key=key,group=group,title=title,icon=icon,endpoint=endpoint,description=description)
        for key,group,title,icon,endpoint,description in CATALOG
        if endpoint in current_app.view_functions and allowed(policy(endpoint,current_app.view_functions[endpoint]),user)]

def cards(user_id,keys):
    choices={tile['key']:tile for tile in permitted(user_id)}
    return [{**choices[key],'url':url_for(choices[key]['endpoint'])} for key in keys if key in choices]
