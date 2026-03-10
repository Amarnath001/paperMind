"""PaperMind Flask application factory."""

import os

from flask import Flask
from flask_cors import CORS

from app.config import Config


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(app)

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
