from sqlalchemy import update
from werkzeug.security import generate_password_hash
from factoryos.extensions import db
from factoryos.models.user import User
from factoryos.core.services.change_log_service import log_change


def change_own_password(user, current_password, new_password, confirmation):
    # Do not trim passwords. Leading/trailing whitespace can be intentional.
    if not current_password or len(current_password) > 1024:
        raise ValueError("Bitte dein aktuelles Passwort eingeben.")
    original_hash = user.password_hash
    if not user.check_password(current_password):
        raise ValueError("Das aktuelle Passwort ist nicht korrekt.")
    if not 12 <= len(new_password) <= 128 or not new_password.strip():
        raise ValueError("Das neue Passwort muss 12 bis 128 Zeichen lang sein und darf nicht nur aus Leerzeichen bestehen.")
    if new_password != confirmation:
        raise ValueError("Die neuen Passwörter stimmen nicht überein.")
    if user.check_password(new_password):
        raise ValueError("Das neue Passwort muss sich vom bisherigen Passwort unterscheiden.")
    replacement = generate_password_hash(new_password)
    result = db.session.execute(update(User).where(
        User.id == user.id, User.active.is_(True), User.password_hash == original_hash
    ).values(password_hash=replacement).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        db.session.rollback()
        raise ValueError("Das Konto oder Passwort wurde zwischenzeitlich geändert. Bitte neu anmelden.")
    # Audit the event only: no plaintext, old hash or new hash in the change log.
    log_change("user", user.id, "password_change", entity_name=user.username,
               category="account", changes={"password_changed": True})
    db.session.commit()
    db.session.expire(user, ["password_hash"])
