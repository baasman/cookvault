import os
import logging
from pathlib import Path

from flask import Flask, send_from_directory, request, session, g, make_response, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import config, load_environment_config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    # Load environment-specific .env file before creating config
    load_environment_config(config_name)

    config_obj = config[config_name]
    app.logger.info(f"🔧 Using configuration: {config_obj.__name__}")

    # Initialize app with dynamic configuration (no from_object needed)
    config_obj.init_app(app)

    # Configure proxy handling for production CDN/proxy setups
    if not app.debug:
        # Handle X-Forwarded-* headers from Cloudflare/Render proxy
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,    # Number of proxies setting X-Forwarded-For
            x_proto=1,  # Number of proxies setting X-Forwarded-Proto
            x_host=1,   # Number of proxies setting X-Forwarded-Host
            x_port=1    # Number of proxies setting X-Forwarded-Port
        )
        app.logger.info("ProxyFix middleware configured for production")

    # Ensure session configuration is properly set
    app.logger.info(f"Session configuration:")
    app.logger.info(f"  SECRET_KEY set: {bool(app.config.get('SECRET_KEY'))}")
    app.logger.info(f"  SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
    app.logger.info(f"  SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}")
    app.logger.info(f"  SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
    app.logger.info(f"  PERMANENT_SESSION_LIFETIME: {app.config.get('PERMANENT_SESSION_LIFETIME')}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    # Configure CORS
    cors_origins = app.config.get('CORS_ORIGINS', ["http://localhost:5173", "http://127.0.0.1:5173"])
    app.logger.info(f"🔧 CORS Origins configured: {cors_origins}")
    
    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,  # Required for cross-origin cookies
        allow_headers=[
            'Content-Type', 
            'Authorization', 
            'X-Requested-With',
            'Accept',
            'Origin',
            'Access-Control-Request-Method',
            'Access-Control-Request-Headers'
        ],
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD'],
        expose_headers=[
            'Content-Type',
            'Authorization'
        ],
        max_age=86400  # Cache preflight for 24 hours
    )
    app.logger.info("🔧 CORS configured with credentials support for secure cookies")

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
            force_https=True,   # Enable HTTPS enforcement in production
            strict_transport_security=True,
            session_cookie_secure=True,  # Use secure cookies (required for SameSite=None)
            session_cookie_samesite='None',  # Required for cross-origin secure cookies
            content_security_policy=csp,
            feature_policy={
                'geolocation': "'none'",
                'camera': "'none'",
                'microphone': "'none'",
            }
        )

    # Configure rate limiting (after dynamic config is loaded)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100/hour')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL')
    )
    limiter.init_app(app)
    app.logger.info(f"Rate limiter configured with default: {app.config.get('RATELIMIT_DEFAULT')}")

    # Ensure upload folder exists (after dynamic config is loaded)
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.logger.info(f"Upload folder configured: {upload_folder}")

    # Set up logging for development only (production logging is handled in config.py)
    if app.debug:
        # Development logging setup
        app.logger.setLevel(logging.DEBUG)

        if not app.logger.hasHandlers():
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

    # Add session debugging middleware
    @app.before_request
    def debug_session_loading():
        """Debug session loading process for troubleshooting"""
        # Only log for API requests to avoid spam
        if request.path.startswith('/api/'):
            app.logger.debug(f"=== SESSION DEBUG: {request.method} {request.path} ===")
            app.logger.debug(f"Request cookies: {dict(request.cookies)}")
            app.logger.debug(f"Session before access: {getattr(g, 'session_loaded', 'not yet loaded')}")

            # Force session loading by accessing it
            try:
                session_data = dict(session)
                app.logger.debug(f"Session data loaded: {session_data}")
                app.logger.debug(f"Session permanent: {session.permanent}")

                # Check if session token exists
                session_token = session.get('session_token')
                if session_token:
                    app.logger.debug(f"Session token found: {session_token[:10]}...")
                else:
                    app.logger.warning(f"No session token in session. Available keys: {list(session.keys())}")

                # Log session cookie configuration at runtime
                app.logger.debug(f"Runtime session config:")
                app.logger.debug(f"  SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
                app.logger.debug(f"  SESSION_COOKIE_DOMAIN: {app.config.get('SESSION_COOKIE_DOMAIN')}")
                app.logger.debug(f"  SESSION_COOKIE_PATH: {app.config.get('SESSION_COOKIE_PATH')}")
                app.logger.debug(f"  SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
                app.logger.debug(f"  SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")

            except Exception as e:
                app.logger.error(f"Session loading failed: {str(e)}")
                import traceback
                app.logger.error(f"Session loading traceback: {traceback.format_exc()}")

            app.logger.debug("=== END SESSION DEBUG ===")

    # Register blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    # Log routes after blueprint registration
    log_routes()

    # Add explicit OPTIONS handler for all API routes to help with CORS preflight
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            # Get the allowed origins
            cors_origins = app.config.get('CORS_ORIGINS', ["http://localhost:5173", "http://127.0.0.1:5173"])
            origin = request.headers.get('Origin')
            
            # Check if origin is allowed
            if origin in cors_origins:
                response = make_response()
                response.headers.add("Access-Control-Allow-Origin", origin)
                response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization,X-Requested-With,Accept,Origin")
                response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS,HEAD")
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                response.headers.add('Access-Control-Max-Age', '86400')
                return response
            else:
                app.logger.warning(f"CORS preflight blocked for origin: {origin}, allowed: {cors_origins}")
                
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
