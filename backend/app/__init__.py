import os
import logging
from pathlib import Path

from flask import Flask, send_from_directory, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    config_name = config_name or os.environ.get("FLASK_ENV", "default")
    config_obj = config[config_name]
    app.config.from_object(config_obj)

    # Initialize config-specific settings
    config_obj.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    # Configure CORS
    cors_origins = app.config.get('CORS_ORIGINS', ["http://localhost:5173", "http://127.0.0.1:5173"])
    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,
        allow_headers=['Content-Type', 'Authorization'],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    )

    # Configure security headers with Talisman
    if not app.debug:
        csp = {
            'default-src': "'self'",
            'img-src': "'self' data: https:",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'font-src': "'self' data:",
        }
        Talisman(
            app,
            force_https=False,  # Set to True when using HTTPS
            strict_transport_security=True,
            content_security_policy=csp,
            feature_policy={
                'geolocation': "'none'",
                'camera': "'none'",
                'microphone': "'none'",
            }
        )

    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100/hour')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL')
    )

    # Create upload folder
    upload_folder = Path(app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(exist_ok=True)

    # Create logs folder for production
    if not app.debug:
        logs_folder = Path("logs")
        logs_folder.mkdir(exist_ok=True)
        
    # Enhanced logging configuration for debugging
    if not app.debug:
        app.logger.setLevel(logging.DEBUG)
    else:
        app.logger.setLevel(logging.DEBUG)
        
    # Add console handler for debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    )
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
    
    # Log all registered routes for debugging (after blueprints are registered)
    def log_routes():
        app.logger.info("=== REGISTERED ROUTES ===")
        for rule in app.url_map.iter_rules():
            methods = ','.join(rule.methods - {'HEAD', 'OPTIONS'})
            app.logger.info(f"{rule.rule} [{methods}] -> {rule.endpoint}")
        app.logger.info("===========================")

    # Register blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Log routes after blueprint registration
    log_routes()
    
    # Add catch-all route for debugging API calls
    @app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def api_catchall(path):
        app.logger.error(f"CATCHALL: Unmatched API route /{path} with method {request.method}")
        app.logger.error(f"CATCHALL: Request headers: {dict(request.headers)}")
        app.logger.error(f"CATCHALL: Full URL: {request.url}")
        return jsonify({
            "error": f"API endpoint not found: /{path}",
            "method": request.method,
            "available_routes": [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api')]
        }), 404

    # Serve static files (frontend build)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve frontend static files or index.html for SPA routing"""
        frontend_build_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"

        if frontend_build_dir.exists():
            if path and (frontend_build_dir / path).exists():
                return send_from_directory(frontend_build_dir, path)
            else:
                # For SPA routing, serve index.html for unknown routes
                return send_from_directory(frontend_build_dir, 'index.html')
        else:
            # Fallback if frontend not built
            return {"message": "Frontend not built. Please run 'npm run build' in the frontend directory."}, 503

    @app.route("/health")
    @limiter.exempt
    def health_check():
        """Health check endpoint for load balancers"""
        return {
            "status": "healthy",
            "service": "cookbook-creator-backend",
            "version": "1.0.0"
        }

    @app.route("/api/health")
    @limiter.exempt
    def api_health_check():
        """Detailed health check for monitoring"""
        import redis
        from sqlalchemy import text

        checks = {
            "database": False,
            "redis": False,
            "uploads": False
        }

        try:
            # Check database connection
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception as e:
            app.logger.error(f"Database health check failed: {e}")

        try:
            # Check Redis connection
            r = redis.from_url(app.config['REDIS_URL'])
            r.ping()
            checks["redis"] = True
        except Exception as e:
            app.logger.error(f"Redis health check failed: {e}")

        try:
            # Check upload folder
            upload_folder = Path(app.config["UPLOAD_FOLDER"])
            checks["uploads"] = upload_folder.exists() and upload_folder.is_dir()
        except Exception as e:
            app.logger.error(f"Upload folder health check failed: {e}")

        all_healthy = all(checks.values())
        status_code = 200 if all_healthy else 503

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "service": "cookbook-creator-backend",
            "version": "1.0.0"
        }, status_code

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal error: {error}")
        return {"error": "Internal server error"}, 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"error": "Rate limit exceeded", "message": str(e.description)}, 429

    return app
