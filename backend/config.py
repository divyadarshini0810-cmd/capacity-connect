import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def database_uri():
    """Return a SQLAlchemy-compatible URL for local SQLite or Render Postgres."""
    value = os.getenv("DATABASE_URL")
    if value:
        # Some providers retain the legacy postgres:// scheme while SQLAlchemy
        # expects postgresql://.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value
    return f"sqlite:///{BASE_DIR / 'capacity_connect.db'}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "capacity-connect-dev-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "capacity-connect-jwt-dev-key")
    # An empty DATABASE_URL deliberately keeps the zero-setup SQLite demo active.
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:4173,http://127.0.0.1:4173,http://localhost:4175,http://127.0.0.1:4175",
    ).split(",")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    BOOTSTRAP_BASELINE_DATA = os.getenv("BOOTSTRAP_BASELINE_DATA", "true").lower() == "true"
