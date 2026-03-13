from factoryos.modules.admin.users.queries.user_queries import (
    get_user,
    create_user,
    update_user,
    delete_user
)


def create_new_user(data):

    if not data.get("username"):
        raise ValueError("Benutzername fehlt")

    if not data.get("password"):
        raise ValueError("Passwort fehlt")

    return create_user(data)


def update_existing_user(user_id, data):

    user = get_user(user_id)

    if not data.get("username"):
        raise ValueError("Benutzername fehlt")

    return update_user(user, data)


def remove_user(user_id):

    user = get_user(user_id)

    delete_user(user)
