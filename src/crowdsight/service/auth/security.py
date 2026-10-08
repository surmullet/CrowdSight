"""Cryptographic authentication, password hashing, and JWT utilities."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from crowdsight.service.storage.models import UserRecord

# JWT Secret & Algorithm
JWT_SECRET_KEY = os.environ.get("CROWDSIGHT_JWT_SECRET", "crowdsight-super-secret-jwt-key-2026-prod")
JWT_ALGORITHM = "HS256"
DEFAULT_TOKEN_EXPIRE_HOURS = 24


class UserRole(str, Enum):
    """User roles for Role-Based Access Control (RBAC)."""
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


def get_password_hash(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and 16-byte salt."""
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:sha256:{iterations}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against pbkdf2 hash in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        header, salt_hex, hash_hex = parts
        prefix, algo, iters_str = header.split(":")
        if prefix != "pbkdf2":
            return False
        iterations = int(iters_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        candidate_hash = hashlib.pbkdf2_hmac(algo, plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(candidate_hash, expected_hash)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=DEFAULT_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate signed JWT access token."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def seed_default_users_if_empty(session: Session) -> None:
    """Seed initial default users (admin, operator, viewer) if users table is empty."""
    existing_count = session.scalar(select(UserRecord.id).limit(1))
    if existing_count is not None:
        return

    defaults = [
        {
            "username": "admin",
            "email": "admin@crowdsight.ai",
            "password": "admin123",
            "role": UserRole.ADMIN.value,
            "full_name": "Quản Trị Viên (Admin)",
        },
        {
            "username": "operator",
            "email": "operator@crowdsight.ai",
            "password": "operator123",
            "role": UserRole.OPERATOR.value,
            "full_name": "Giám Sát Viên (Operator)",
        },
        {
            "username": "viewer",
            "email": "viewer@crowdsight.ai",
            "password": "viewer123",
            "role": UserRole.VIEWER.value,
            "full_name": "Khách Xem (Viewer)",
        },
    ]

    for item in defaults:
        user = UserRecord(
            username=item["username"],
            email=item["email"],
            hashed_password=get_password_hash(item["password"]),
            role=item["role"],
            full_name=item["full_name"],
            is_active=True,
        )
        session.add(user)
    session.commit()
