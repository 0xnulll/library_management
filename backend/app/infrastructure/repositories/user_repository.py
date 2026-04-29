from __future__ import annotations

from sqlalchemy import select

from app.domain.entities import StaffUser
from app.infrastructure.db.models import StaffUserModel
from app.infrastructure.repositories.base_repository import BaseRepository


def _to_entity(row: StaffUserModel) -> StaffUser:
    return StaffUser(
        id=row.id,
        username=row.username,
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=row.created_at,
    )


class SqlUserRepository(BaseRepository):
    def get_by_username(self, username: str) -> StaffUser | None:
        stmt = select(StaffUserModel).where(StaffUserModel.username == username)
        row = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(row) if row else None

    def add(self, user: StaffUser) -> StaffUser:
        row = StaffUserModel(
            username=user.username,
            password_hash=user.password_hash,
            is_active=user.is_active,
        )
        self._session.add(row)
        self._session.flush()
        return _to_entity(row)
