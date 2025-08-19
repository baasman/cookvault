import os
import secrets
from pathlib import Path
from typing import Type

from dotenv import load_dotenv

# Initialize project root
project_root = Path(__file__).parent.parent.parent


def load_environment_config(config_name: str = None):
    """Load environment-specific .env file"""
    # Default to development if no config specified
    config_name = config_name or "development"

    # Map config names to env file names
    env_file_mapping = {
        "development": ".env",
        "testing": ".env.testing",
        "production": ".env.production",
        "default": ".env",
    }

    env_filename = env_file_mapping.get(config_name, ".env")
    env_path = project_root / env_filename

    # Load the specific env file, fallback to .env if the specific file doesn't exist
    if env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        # Fallback to .env
        fallback_path = project_root / ".env"
        if fallback_path.exists():
            load_dotenv(fallback_path)


# Load default .env for backwards compatibility (will be overridden by load_environment_config)
default_env_path = project_root / ".env"
if default_env_path.exists():
    load_dotenv(default_env_path)

db_path = Path(__file__).parents[2] / "dbs"


class Config:
    # Static settings that don't need environment variables
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_PATH = "/"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    RATELIMIT_DEFAULT = "100/hour"
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @classmethod
    def init_app(cls, app):
        """Initialize app with dynamic configuration from environment variables"""
        # Static settings (formerly from class attributes)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['WTF_CSRF_ENABLED'] = True
        app.config['WTF_CSRF_TIME_LIMIT'] = None
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_PATH'] = "/"
        app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get("PERMANENT_SESSION_LIFETIME", 3600))
        app.config['RATELIMIT_DEFAULT'] = "100/hour"
        app.config['CORS_ORIGINS'] = ["http://localhost:5173", "http://127.0.0.1:5173"]
        
        # Image optimization settings (same in all environments)
        app.config['MAX_IMAGE_DIMENSION'] = int(os.environ.get("MAX_IMAGE_DIMENSION", 1200))
        app.config['JPEG_QUALITY'] = int(os.environ.get("JPEG_QUALITY", 85))
        app.config['MAX_UPLOAD_SIZE'] = int(os.environ.get("MAX_UPLOAD_SIZE", 8))  # MB

        # Default debug/testing flags (can be overridden by subclasses)
        app.config['DEBUG'] = False
        app.config['TESTING'] = False

        # Load dynamic config values at runtime
        app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY") or "dev-secret-key"
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") or "sqlite:///cookbook.db"
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
        app.config['REDIS_URL'] = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
        app.config['UPLOAD_FOLDER'] = Path(__file__).parent.parent / os.environ.get("UPLOAD_FOLDER", "uploads")
        app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
        app.config['ANTHROPIC_API_KEY'] = os.environ.get("ANTHROPIC_API_KEY")
        app.config['GOOGLE_BOOKS_API_KEY'] = os.environ.get("GOOGLE_BOOKS_API_KEY")

        # Stripe payment settings
        app.config['STRIPE_SECRET_KEY'] = os.environ.get("STRIPE_SECRET_KEY")
        app.config['STRIPE_PUBLISHABLE_KEY'] = os.environ.get("STRIPE_PUBLISHABLE_KEY")
        app.config['STRIPE_WEBHOOK_SECRET'] = os.environ.get("STRIPE_WEBHOOK_SECRET")
        app.config['STRIPE_PREMIUM_PRICE'] = int(os.environ.get("STRIPE_PREMIUM_PRICE", 299))  # $2.99 in cents
        app.config['FREE_TIER_UPLOAD_LIMIT'] = int(os.environ.get("FREE_TIER_UPLOAD_LIMIT", 10))

        # OCR Quality and LLM fallback settings
        app.config['OCR_QUALITY_THRESHOLD'] = int(os.environ.get("OCR_QUALITY_THRESHOLD", 8))
        app.config['OCR_ENABLE_LLM_FALLBACK'] = os.environ.get("OCR_ENABLE_LLM_FALLBACK", "true").lower() == "true"
        app.config['OCR_QUALITY_CACHE_TTL'] = int(os.environ.get("OCR_QUALITY_CACHE_TTL", 3600))

        # Session security settings - default to secure for HTTPS production
        _session_secure_env = os.environ.get("SESSION_COOKIE_SECURE", "true")
        _session_secure_parsed = _session_secure_env.lower() == "true"

        app.config['SESSION_COOKIE_SECURE'] = _session_secure_parsed
        # Set the session cookie domain for production - only if explicitly provided
        # For cross-origin to work, the domain must be explicitly set to allow sharing
        session_cookie_domain_env = os.environ.get("SESSION_COOKIE_DOMAIN")
        app.logger.info(f"SESSION_COOKIE_DOMAIN env var: '{session_cookie_domain_env}'")
        if session_cookie_domain_env:
            app.config['SESSION_COOKIE_DOMAIN'] = session_cookie_domain_env
            app.logger.info(f"✓ Session cookie domain set to: {session_cookie_domain_env}")
        else:
            # Don't set a domain - let browser use the request domain
            app.logger.warning("⚠️  SESSION_COOKIE_DOMAIN not set - using request domain (may cause cross-origin issues)")
            app.config['SESSION_COOKIE_DOMAIN'] = None

        # Configure session cookie settings
        app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get(
            "SESSION_COOKIE_SAMESITE", "None" if _session_secure_parsed else "Lax"
        )

        # Rate limiting
        app.config['RATELIMIT_STORAGE_URL'] = os.environ.get("REDIS_URL") or "redis://localhost:6379/1"

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


class DevelopmentConfig(Config):
    @classmethod
    def init_app(cls, app):
        """Development-specific initialization"""
        # Call parent init_app first
        super().init_app(app)

        # Override with development-specific settings
        app.config['DEBUG'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}/cookbook_db_dev.db"


class TestingConfig(Config):
    @classmethod
    def init_app(cls, app):
        """Testing-specific initialization"""
        # Call parent init_app first
        super().init_app(app)

        # Override with testing-specific settings
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}/cookbook_db_test.db"


class ProductionConfig(Config):
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization"""
        # Call parent init_app first
        super().init_app(app)

        # Production-specific settings
        app.config['DEBUG'] = False
        app.config['TESTING'] = False

        # Production database with connection pooling
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            "pool_size": 10,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
            "max_overflow": 20,
        }

        # Production CORS - should be updated with actual frontend domains
        cors_origins_env = os.environ.get("CORS_ORIGINS", "")
        if cors_origins_env:
            # Clean up origins and remove empty strings
            cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
            app.config['CORS_ORIGINS'] = cors_origins
            app.logger.info(f"Production CORS origins loaded from env: {cors_origins}")
        else:
            app.logger.warning("No CORS_ORIGINS environment variable set for production!")

        # Stricter rate limiting for production
        app.config['RATELIMIT_DEFAULT'] = "60/hour"
        
        # Disable heavy image preprocessing in production to save memory
        app.config['SKIP_IMAGE_PREPROCESSING'] = True
        
        # Balanced image optimization settings for OCR quality vs memory
        app.config['MAX_IMAGE_DIMENSION'] = int(os.environ.get("MAX_IMAGE_DIMENSION", 1568))  # Higher for better OCR
        app.config['JPEG_QUALITY'] = int(os.environ.get("JPEG_QUALITY", 95))  # Higher quality for better text recognition
        app.config['MAX_UPLOAD_SIZE'] = int(os.environ.get("MAX_UPLOAD_SIZE", 8))  # Max 8MB uploads

        # Production logging
        app.config['LOG_LEVEL'] = os.environ.get("LOG_LEVEL", "WARNING")

        # Validate required environment variables
        cls.validate_required_env_vars()

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
        log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper())
        app.logger.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]"
        )

        # Ensure logs directory exists
        log_file_path = Path(app.config.get("LOG_FILE", "logs/cookbook-creator.log"))
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        # File handler for all logs
        file_handler = RotatingFileHandler(
            app.config.get("LOG_FILE", "logs/cookbook-creator.log"),
            maxBytes=app.config.get("LOG_MAX_BYTES", 10 * 1024 * 1024),
            backupCount=app.config.get("LOG_BACKUP_COUNT", 10),
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
