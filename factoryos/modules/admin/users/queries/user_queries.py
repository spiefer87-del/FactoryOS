from factoryos.extensions import db
from factoryos.models.user import User


def get_all_users():

    return (
        User.query
        .order_by(User.username.asc())
        .all()
    )


def get_user(user_id):

    return User.query.get_or_404(user_id)


def create_user(data):

    user = User(
        username=data.get("username"),
        role=data.get("role")
    )

    if data.get("password"):
        user.set_password(data.get("password"))

    db.session.add(user)
    db.session.commit()

    return user


def update_user(user, data):

    user.username = data.get("username")
    user.role = data.get("role")

    if data.get("password"):
        user.set_password(data.get("password"))

    db.session.commit()

    return user


def delete_user(user):

    db.session.delete(user)
    db.session.commit()
