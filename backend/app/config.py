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
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "None" if os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true" else "Lax")
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_DOMAIN = os.environ.get("SESSION_COOKIE_DOMAIN")  # None for same-origin only
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Additional session configuration for production with CDN
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_NAME = "session"

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/1"
    RATELIMIT_DEFAULT = "100/hour"

    # CORS settings
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", "logs/cookbook-creator.log")
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))

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
        
        # Additional validation for SECRET_KEY
        secret_key = os.environ.get("SECRET_KEY")
        if secret_key and len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long for security")

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

    # Production security settings - inherit from base config with env var override
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
        
        # Log critical configuration for debugging
        app.logger.info("=== PRODUCTION CONFIG VALIDATION ===")
        app.logger.info(f"SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")
        app.logger.info(f"SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
        app.logger.info(f"SESSION_COOKIE_DOMAIN: {app.config.get('SESSION_COOKIE_DOMAIN')}")
        app.logger.info(f"DATABASE_URL set: {bool(app.config.get('DATABASE_URL'))}")
        app.logger.info("=====================================")

        # Set up production logging
        cls._setup_production_logging(app)

    @staticmethod
    def _setup_production_logging(app):
        """Configure production logging with both file and console handlers"""
        import logging
        from logging.handlers import RotatingFileHandler
        import sys

        # Clear any existing handlers to avoid duplicates
        if app.logger.hasHandlers():
            app.logger.handlers.clear()

        # Set logger level
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
        app.logger.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]'
        )

        # Ensure logs directory exists
        log_file_path = Path(app.config.get('LOG_FILE', "logs/cookbook-creator.log"))
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # File handler for all logs
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', "logs/cookbook-creator.log"), 
            maxBytes=app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024),
            backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)

        # Console handler for stdout (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        app.logger.addHandler(console_handler)

        # Error handler for stderr (WARNING and above)
        error_handler = logging.StreamHandler(sys.stderr)
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.WARNING)
        app.logger.addHandler(error_handler)

        # Prevent propagation to avoid duplicate logs
        app.logger.propagate = False

        app.logger.info("Production logging configured - writing to file and console")


config: dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
