#!/usr/bin/env python3
"""Root-only setup; never print, copy, prompt for or send the API credential."""
import os
import re
import stat
import tempfile
from pathlib import Path

SECRET = Path('/etc/factoryos-secrets/groq.env')
DROPIN = Path('/etc/systemd/system/factoryos.service.d/50-groq-vision.conf')
CONTENT = '''# FactoryOS opt-in vision. Credential stays outside the repository.
[Service]
EnvironmentFile=/etc/factoryos-secrets/groq.env
Environment=FACTORYOS_GROQ_ENABLED=1
Environment=FACTORYOS_GROQ_FREE_CONFIRMED=1
'''


def configure():
    if os.geteuid()!=0:
        raise ValueError('Bitte über das Installationsskript mit sudo ausführen.')
    for path in (SECRET.parent,SECRET):
        info=path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o077:
            raise ValueError('Schlüsselablage muss root gehören, ohne Gruppen-/Fremdzugriff und ohne Symlinks.')
    if not SECRET.is_file() or SECRET.stat().st_size>1000:
        raise ValueError('Schlüsseldatei fehlt oder ist ungültig.')
    if not re.fullmatch(r'GROQ_API_KEY=[A-Za-z0-9_.-]{20,300}\n?',SECRET.read_text()):
        raise ValueError('Schlüsseldatei hat nicht das erwartete Format. Inhalt wird nicht ausgegeben.')
    if DROPIN.parent.is_symlink() or DROPIN.is_symlink():
        raise ValueError('Symlink in Dienstkonfiguration; keine Änderung vorgenommen.')
    if DROPIN.exists():
        if DROPIN.read_text()!=CONTENT:
            raise ValueError('Abweichende Groq-Dienstkonfiguration vorhanden. Wird nicht überschrieben.')
        print('Groq-Dienstkonfiguration bereits eingerichtet. Schlüssel bleibt unverändert.')
        return
    print('Fotos gehen nur nach Auswahl und Einzelbestätigung an Groq. Datenschutz/ZDR im Konto prüfen.')
    print('Der Tarif ist technisch nicht prüfbar. Ein bezahlter Groq-Tarif kann Kosten verursachen.')
    print('Lokales Limit: 10 Versuche/UTC-Tag. Keine automatische Wiederholung oder Tarifänderung.')
    if input('Nur mit deinem Free-Konto verwenden. Zur Aktivierung FREE eingeben: ').strip()!='FREE':
        raise ValueError('Aktivierung abgebrochen. Keine Dienstkonfiguration verändert.')
    DROPIN.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    name=None
    try:
        fd,name=tempfile.mkstemp(prefix='.groq-config-',dir=DROPIN.parent)
        with os.fdopen(fd,'w') as stream:
            stream.write(CONTENT);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,0o644)
        # Link with O_EXCL semantics: never overwrite an intervening administrator edit.
        os.link(name,DROPIN)
    finally:
        if name and os.path.exists(name):os.unlink(name)
    print('Groq-Dienstkonfiguration angelegt. Schlüssel wurde weder kopiert noch angezeigt.')


if __name__=='__main__':
    try:configure()
    except (ValueError,OSError,UnicodeError,EOFError):
        # Exceptions involving file access must not disclose file contents.
        print('Einrichtung nicht abgeschlossen. Schlüsselablage/Berechtigungen oder vorhandene Konfiguration prüfen; nichts überschreiben.')
        raise SystemExit(1)
