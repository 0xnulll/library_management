from __future__ import annotations

from sqlalchemy import select

from app.domain.entities import Member
from app.infrastructure.db.models import MemberModel
from app.infrastructure.repositories.base_repository import BaseRepository


def _to_entity(row: MemberModel) -> Member:
    return Member(
        id=row.id,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlMemberRepository(BaseRepository):
    def add(self, member: Member) -> Member:
        row = MemberModel(
            full_name=member.full_name,
            email=member.email,
            phone=member.phone,
        )
        self._session.add(row)
        self._session.flush()
        return _to_entity(row)

    def get(self, member_id: int) -> Member | None:
        row = self._session.get(MemberModel, member_id)
        return _to_entity(row) if row else None

    def get_by_email(self, email: str) -> Member | None:
        stmt = select(MemberModel).where(MemberModel.email == email)
        row = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(row) if row else None

    def update(self, member: Member) -> Member:
        row = self._session.get(MemberModel, member.id)
        if row is None:
            raise ValueError(f"member {member.id} not found")
        row.full_name = member.full_name
        row.email = member.email
        row.phone = member.phone
        self._session.flush()
        return _to_entity(row)

    def list(self, limit: int, offset: int) -> list[Member]:
        stmt = select(MemberModel).order_by(MemberModel.full_name.asc()).limit(limit).offset(offset)
        return [_to_entity(r) for r in self._session.execute(stmt).scalars().all()]
