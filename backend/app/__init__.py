"""PaperMind Flask application factory."""

import logging
import os
import time
from typing import Any

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config

logger = logging.getLogger("papermind")

limiter: Limiter | None = None


def _configure_logging() -> None:
    # Basic structured logging to stdout suitable for containerised deployments.
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application."""
    _configure_logging()

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Log storage config at startup
    provider = (app.config.get("STORAGE_PROVIDER") or "local").lower()
    if provider == "s3":
        bucket = app.config.get("S3_BUCKET_NAME") or ""
        endpoint = (app.config.get("S3_ENDPOINT_URL") or "")[:50]
        logger.info(
            "storage provider=s3 bucket=%s endpoint=%s...",
            bucket or "(not set)",
            endpoint or "(default)",
        )
    else:
        logger.info("storage provider=local folder=%s", app.config.get("UPLOAD_FOLDER"))

    # Ensure upload directory exists for local storage
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # CORS: explicit origins for Vercel frontend + local dev; supports credentials (e.g. Authorization header)
    origins = app.config.get("CORS_ORIGINS") or [
        "https://paper-mind-six.vercel.app",
        "http://localhost:3000",
    ]
    CORS(
        app,
        origins=origins,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        expose_headers=[],
    )

    # Rate limiting
    global limiter
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[],
        storage_uri=app.config.get("REDIS_URL", "memory://"),
    )

    @app.before_request
    def _start_timer() -> None:  # type: ignore[override]
        g._start_time = time.time()

    @app.before_request
    def _handle_options_preflight():  # type: ignore[override]
        """Respond to OPTIONS (preflight) with 200 so Flask-CORS can attach CORS headers."""
        if request.method == "OPTIONS":
            from flask import make_response

            return make_response(("", 200))


    @app.after_request
    def _log_request(response: Response) -> Response:  # type: ignore[override]
        try:
            duration = time.time() - getattr(g, "_start_time", time.time())
            extra: dict[str, Any] = {
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": int(duration * 1000),
            }
            logger.info(
                "request",
                extra=extra,
            )
        except Exception:
            # Logging must never break responses
            logger.exception("Failed to log request")
        return response

    @app.errorhandler(HTTPException)
    def _handle_http_exception(exc: HTTPException):  # type: ignore[override]
        """Return proper status code for Flask/Werkzeug HTTP exceptions (e.g. 404)."""
        return jsonify(
            {"error": exc.name or "error", "message": exc.description or ""}
        ), exc.code

    @app.errorhandler(Exception)
    def _handle_uncaught_error(exc: Exception):  # type: ignore[override]
        """Log and return 500 only for unexpected exceptions."""
        logger.exception("Unhandled exception: %s", exc)
        return jsonify({"error": "internal_server_error"}), 500

    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.auth import auth_bp
    from app.routes.workspaces import workspaces_bp
    from app.routes.papers import papers_bp
    from app.routes.jobs import jobs_bp
    from app.routes.search import search_bp
    from app.routes.chat import chat_bp
    from app.routes.insights import insights_bp

    app.register_blueprint(health_bp, url_prefix="")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(workspaces_bp, url_prefix="/workspaces")
    app.register_blueprint(papers_bp, url_prefix="/papers")
    app.register_blueprint(jobs_bp, url_prefix="/jobs")
    app.register_blueprint(search_bp, url_prefix="/search")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(insights_bp, url_prefix="/insights")

    return app
