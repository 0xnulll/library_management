from __future__ import annotations

from app.domain.entities import Member
from app.domain.exceptions import ConflictError, NotFoundError
from app.infrastructure.repositories import SqlMemberRepository
from app.services.response_type import MemberResponse


class MemberService:
    def __init__(self, members: SqlMemberRepository) -> None:
        self._members = members

    def _to_response(self, member: Member) -> MemberResponse:
        return MemberResponse(
            id=member.id or 0,
            full_name=member.full_name,
            email=member.email,
            phone=member.phone,
            created_at=member.created_at,
            updated_at=member.updated_at,
        )

    def create(self, *, full_name: str, email: str, phone: str | None) -> MemberResponse:
        if self._members.get_by_email(email):
            raise ConflictError(f"member with email {email} already exists")
        member = Member(
            id=None,
            full_name=full_name,
            email=email,
            phone=phone,
        )
        return self._to_response(self._members.add(member))

    def update(
        self, member_id: int, *, full_name: str, email: str, phone: str | None
    ) -> MemberResponse:
        existing = self._members.get(member_id)
        if existing is None:
            raise NotFoundError(f"member {member_id} not found")
        other = self._members.get_by_email(email)
        if other and other.id != member_id:
            raise ConflictError("email already used by another member")
        existing.full_name = full_name
        existing.email = email
        existing.phone = phone
        return self._to_response(self._members.update(existing))

    def get(self, member_id: int) -> MemberResponse:
        member = self._members.get(member_id)
        if member is None:
            raise NotFoundError(f"member {member_id} not found")
        return self._to_response(member)

    def list(self, limit: int, offset: int) -> list[MemberResponse]:
        return [self._to_response(m) for m in self._members.list(limit, offset)]
