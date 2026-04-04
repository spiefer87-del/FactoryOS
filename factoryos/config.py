import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_DRAWINGS = os.path.join(BASE_DIR, "static/qm_drawings")
UPLOAD_SNIPPETS = os.path.join(BASE_DIR, "static/qm_snippets")
UPLOAD_IDENTIFICATION = os.path.join(BASE_DIR, "static/qm_identification")

class Config:

    SECRET_KEY = "factoryos-secret-key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///factoryos.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

