"""Session signing key outside source control. Never log or return the key."""
import os
import secrets
from pathlib import Path


def key_path():
    return Path(os.environ.get("FACTORYOS_SECRET_KEY_FILE") or Path(__file__).resolve().parents[2] / "instance" / "session_secret.key")


def load_session_secret():
    supplied = os.environ.get("FACTORYOS_SECRET_KEY")
    if supplied:
        if len(supplied) < 32:
            raise RuntimeError("FACTORYOS_SECRET_KEY muss mindestens 32 Zeichen lang sein.")
        return supplied
    path = key_path()
    if path.is_symlink():
        raise RuntimeError("Sitzungsschlüssel darf kein symbolischer Link sein.")
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if len(value) < 32 or path.stat().st_mode & 0o077:
        raise RuntimeError("Privater Sitzungsschlüssel fehlt, ist zu kurz oder hat zu offene Dateirechte (0600 erforderlich).")
    return value


def ensure_session_secret():
    if os.environ.get("FACTORYOS_SECRET_KEY"):
        load_session_secret()
        print("Privater Sitzungsschlüssel aus Umgebung vorhanden.")
        return
    path = key_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:
        load_session_secret()
        print("Vorhandener privater Sitzungsschlüssel bleibt unverändert.")
        return
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(secrets.token_hex(48) + "\n")
    print("Privater Sitzungsschlüssel angelegt. Nach Neustart einmal neu anmelden.")
