from __future__ import annotations

import json
from typing import Generator

import pytest

from app import create_app


@pytest.fixture
def client() -> Generator:
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    with app.test_client() as client:
        yield client


def test_healthz(client) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_auth_signup_login_validation(client) -> None:
    # Missing payload
    resp = client.post("/auth/signup", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400

    resp = client.post("/auth/login", data=json.dumps({}), content_type="application/json")
    assert resp.status_code == 400

