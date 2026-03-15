from factoryos.extensions import db


def create_row(model, data):

    row = model(**data)

    db.session.add(row)
    db.session.commit()

    return row


def update_row(row, data):

    for key, value in data.items():

        setattr(row, key, value)

    db.session.commit()

    return row


def delete_row(row):

    db.session.delete(row)
    db.session.commit()