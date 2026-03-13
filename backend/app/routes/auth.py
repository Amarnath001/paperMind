from __future__ import annotations

from flask import Blueprint, jsonify, request

from app import limiter

from app.services.auth_service import (
    create_access_token,
    create_user,
    get_current_user,
    get_user_by_email,
    require_auth,
    verify_password,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("5/minute")  # type: ignore[arg-type]
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    existing = get_user_by_email(email)
    if existing:
        return jsonify({"error": "user with this email already exists"}), 409

    user = create_user(email, password)
    token = create_access_token(user["id"])

    return (
        jsonify(
            {
                "token": token,
                "user": {
                    "id": str(user["id"]),
                    "email": user["email"],
                    "created_at": user["created_at"].isoformat(),
                },
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")  # type: ignore[arg-type]
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "invalid credentials"}), 401

    token = create_access_token(user["id"])

    return jsonify(
        {
            "token": token,
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "created_at": user["created_at"].isoformat(),
            },
        }
    )


@auth_bp.route("/me", methods=["GET"])
def me():
    try:
        user = require_auth()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 401

    return jsonify(
        {
            "id": str(user["id"]),
            "email": user["email"],
            "created_at": user["created_at"].isoformat(),
        }
    )

