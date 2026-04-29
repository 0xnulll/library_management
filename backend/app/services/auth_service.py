from __future__ import annotations

from app.core.config import Settings
from app.core.security import JWTEncoder, PasswordHasher
from app.domain.entities import StaffUser
from app.domain.exceptions import AuthenticationError
from app.infrastructure.repositories import SqlUserRepository
from app.services.response_type import TokenResponse


class AuthService:
    def __init__(
        self,
        users: SqlUserRepository,
        hasher: PasswordHasher,
        encoder: JWTEncoder,
        settings: Settings,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._encoder = encoder
        self._settings = settings

    def login(self, username: str, password: str) -> TokenResponse:
        user = self._users.get_by_username(username)
        if user is None or not user.is_active:
            raise AuthenticationError("invalid credentials")
        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        token = self._encoder.encode(subject=user.username)
        return TokenResponse(
            access_token=token,
            expires_in=self._settings.jwt_expires_minutes * 60,
        )

    def ensure_seed_user(self, username: str, password: str) -> StaffUser:
        existing = self._users.get_by_username(username)
        if existing:
            return existing
        return self._users.add(
            StaffUser(
                id=None,
                username=username,
                password_hash=self._hasher.hash(password),
                is_active=True,
            )
        )
