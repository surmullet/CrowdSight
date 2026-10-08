"""Tests for authentication, password hashing, JWT, and Role-Based Access Control (RBAC)."""
from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crowdsight.service.api.app import create_app
from crowdsight.service.api.deps import get_db
from crowdsight.service.auth.security import (
    get_password_hash,
    seed_default_users_if_empty,
    verify_password,
)
from crowdsight.service.storage.models import Base


def test_password_hashing_and_verification() -> None:
    raw = "MySecurePassword123!"
    hashed = get_password_hash(raw)
    assert hashed.startswith("pbkdf2:sha256:100000$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


@pytest.fixture
def auth_client(tmp_path: object) -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_default_users_if_empty(session)

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_login_and_token_generation(auth_client: TestClient) -> None:
    resp = auth_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"

    # Login failed with wrong password
    bad_resp = auth_client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad_resp.status_code == 401


def test_get_me_endpoint(auth_client: TestClient) -> None:
    # Login as operator
    login_resp = auth_client.post("/api/v1/auth/login", json={"username": "operator", "password": "operator123"})
    token = login_resp.json()["access_token"]

    # Call /me with Bearer token
    me_resp = auth_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "operator"
    assert me_resp.json()["role"] == "OPERATOR"

    # Call /me without token fails with 401
    unauth_resp = auth_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401


def test_rbac_admin_vs_viewer(auth_client: TestClient) -> None:
    admin_token = auth_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    viewer_token = auth_client.post(
        "/api/v1/auth/login", json={"username": "viewer", "password": "viewer123"}
    ).json()["access_token"]

    # Admin can list users
    users_resp = auth_client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 3

    # Viewer gets 403 Forbidden
    forbidden_resp = auth_client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {viewer_token}"})
    assert forbidden_resp.status_code == 403
