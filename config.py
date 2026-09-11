import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "True") == "True"

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "asset_management")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")

    AI_PROVIDER = os.environ.get("AI_PROVIDER", "local")
    AI_API_KEY = os.environ.get("AI_API_KEY", "")

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), "exports")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB uploads
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
