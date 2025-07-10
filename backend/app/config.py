import os
from pathlib import Path
from typing import Type

from dotenv import load_dotenv

load_dotenv()

db_path = Path(__file__).parents[2] / "dbs"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///cookbook.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    UPLOAD_FOLDER = (
        Path(__file__).parent.parent / os.environ.get("UPLOAD_FOLDER", "uploads")
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}/cookbook_db_dev.db"


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}/cookbook_db_test.db"


class ProductionConfig(Config):
    DEBUG = False


config: dict[str, Type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
