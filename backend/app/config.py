import os
import secrets
from pathlib import Path
from typing import Type

from dotenv import load_dotenv

load_dotenv()

db_path = Path(__file__).parents[2] / "dbs"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///cookbook.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    UPLOAD_FOLDER = Path(__file__).parent.parent / os.environ.get(
        "UPLOAD_FOLDER", "uploads"
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY")

    # OCR Quality and LLM fallback settings
    OCR_QUALITY_THRESHOLD = int(
        os.environ.get("OCR_QUALITY_THRESHOLD", 8)
    )  # 1-10 scale
    OCR_ENABLE_LLM_FALLBACK = (
        os.environ.get("OCR_ENABLE_LLM_FALLBACK", "true").lower() == "true"
    )
    OCR_QUALITY_CACHE_TTL = int(os.environ.get("OCR_QUALITY_CACHE_TTL", 3600))  # 1 hour

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/1"
    RATELIMIT_DEFAULT = "100/hour"

    # CORS settings
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    @staticmethod
    def validate_required_env_vars():
        """Validate that required environment variables are set"""
        required_vars = ["SECRET_KEY"]
        missing_vars = []

        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")

    @classmethod
    def init_app(cls, app):
        """Base configuration initialization"""
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}/cookbook_db_dev.db"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}/cookbook_db_test.db"


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

    # Production security settings
    SESSION_COOKIE_SECURE = True  # Requires HTTPS
    WTF_CSRF_ENABLED = True

    # Production database with connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
        "max_overflow": 20,
    }

    # Production CORS - should be updated with actual frontend domains
    CORS_ORIGINS = (
        os.environ.get("CORS_ORIGINS", "").split(",")
        if os.environ.get("CORS_ORIGINS")
        else []
    )

    # Stricter rate limiting for production
    RATELIMIT_DEFAULT = "60/hour"

    # Production logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")

    @classmethod
    def init_app(cls, app):
        """Production-specific initialization"""
        Config.init_app(app)

        # Validate required environment variables
        cls.validate_required_env_vars()

        # Set up production logging
        import logging
        from logging.handlers import RotatingFileHandler
        import os

        if not app.debug and not app.testing:
            # Ensure logs directory exists
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)
            
            file_handler = RotatingFileHandler(
                "logs/cookvault.log", maxBytes=10240000, backupCount=10
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info("CookVault startup")


config: dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
