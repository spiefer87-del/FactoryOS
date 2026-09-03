import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

UPLOAD_DRAWINGS = os.path.join(BASE_DIR, "static/qm_drawings")
UPLOAD_SNIPPETS = os.path.join(BASE_DIR, "static/qm_snippets")
UPLOAD_IDENTIFICATION = os.path.join(BASE_DIR, "static/qm_identification")

class Config:

    SECRET_KEY = "factoryos-secret-key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///factoryos.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    FACTORYOS_STORAGE_ROOT = os.environ.get(
        "FACTORYOS_STORAGE_ROOT",
        os.path.join(PROJECT_ROOT, "instance", "storage")
    )

    MAX_CONTENT_LENGTH = int(
        os.environ.get(
            "FACTORYOS_MAX_UPLOAD_BYTES",
            64 * 1024 * 1024
        )
    )

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

