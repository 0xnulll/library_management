from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import Settings


class PasswordHasher:
    """Single responsibility: hash and verify passwords."""

    def __init__(self) -> None:
        self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, password: str) -> str:
        return self._ctx.hash(password)

    def verify(self, password: str, hashed: str) -> bool:
        return self._ctx.verify(password, hashed)


class JWTEncoder:
    """Issue and decode signed access tokens."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._expires_minutes = settings.jwt_expires_minutes

    def encode(self, subject: str, claims: dict[str, Any] | None = None) -> str:
        now = datetime.now(tz=UTC)
        payload: dict[str, Any] = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._expires_minutes)).timestamp()),
        }
        if claims:
            payload.update(claims)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])
