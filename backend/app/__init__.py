"""PaperMind Flask application factory."""

from flask import Flask
from flask_cors import CORS

from app.config import Config


def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)

    # Register blueprints
    from app.routes.health import health_bp

    app.register_blueprint(health_bp, url_prefix="")

    return app
