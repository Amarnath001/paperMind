"""Health check routes."""

import psycopg2
import redis
from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


def _check_database() -> tuple[bool, str]:
    """Test PostgreSQL connectivity. Returns (ok, message)."""
    try:
        conn = psycopg2.connect(current_app.config["DATABASE_URL"])
        conn.close()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def _check_redis() -> tuple[bool, str]:
    """Test Redis connectivity. Returns (ok, message)."""
    try:
        r = redis.from_url(current_app.config["REDIS_URL"])
        r.ping()
        return True, "ok"
    except Exception as e:
        return False, str(e)


@health_bp.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint for container orchestration and load balancers."""
    return jsonify({"status": "ok"}), 200


@health_bp.route("/readyz", methods=["GET"])
def readyz():
    """Readiness check: verifies PostgreSQL and Redis are reachable."""
    db_ok, db_msg = _check_database()
    redis_ok, redis_msg = _check_redis()

    if db_ok and redis_ok:
        return (
            jsonify(
                {
                    "status": "ready",
                    "database": "ok",
                    "redis": "ok",
                }
            ),
            200,
        )

    payload = {
        "status": "not ready",
        "database": "ok" if db_ok else "fail",
        "redis": "ok" if redis_ok else "fail",
    }
    if not db_ok:
        payload["database_error"] = db_msg
    if not redis_ok:
        payload["redis_error"] = redis_msg

    return jsonify(payload), 503
