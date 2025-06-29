import os
from pathlib import Path

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config[config_name])
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    CORS(
        app,
        origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        supports_credentials=True
    )
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(exist_ok=True)
    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/health")
    def health_check():
        return {"status": "healthy", "service": "cookbook-creator-backend"}

    return app
