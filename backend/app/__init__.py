import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from pathlib import Path

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])


def create_app(config_object="config.Config"):
    # Works with both `flask run` and direct Python/WGI launches.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app = Flask(__name__)
    app.config.from_object(config_object)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    from .routes import api
    app.register_blueprint(api, url_prefix="/api")
    # New non-destructive tables are available immediately in the local demo.
    # Production deployments should apply the matching migration before release.
    with app.app_context():
        db.create_all()
        # A new hosted database starts empty. Add only the minimum, public
        # catalogue needed for registration; never overwrite existing records.
        if app.config.get("BOOTSTRAP_BASELINE_DATA") and not app.config.get("TESTING"):
            from .bootstrap import ensure_platform_baseline
            ensure_platform_baseline()

    frontend_dist_value = os.getenv("FRONTEND_DIST")
    frontend_dist = Path(frontend_dist_value) if frontend_dist_value else None
    if frontend_dist and frontend_dist.is_dir():
        @app.get("/")
        @app.get("/<path:path>")
        def serve_frontend(path=""):
            """Serve the built React app and keep its client-side routes usable."""
            if path.startswith("api/"):
                return jsonify(error="API route not found."), 404
            requested_file = frontend_dist / path
            if path and requested_file.is_file():
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, "index.html")

    @app.after_request
    def apply_api_cors(response):
        """Keep local preview origins explicit, even for framework-generated OPTIONS responses."""
        origin = request.headers.get("Origin")
        if request.path.startswith("/api/") and origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers.add("Vary", "Origin")
        return response

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="File is larger than the allowed upload limit."), 413
    return app
