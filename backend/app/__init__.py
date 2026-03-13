"""PaperMind Flask application factory."""

import logging
import os
import time
from typing import Any

from flask import Flask, Request, Response, g, request
from flask_cors import CORS
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

    # Ensure upload directory exists for local storage
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # CORS – can be tightened further via env/config if needed
    CORS(app)

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

    @app.errorhandler(Exception)
    def _handle_uncaught_error(exc: Exception):  # type: ignore[override]
        logger.exception("Unhandled exception: %s", exc)
        from flask import jsonify

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
