"""Internal view models returned by application services.

These are deliberately plain dataclasses (no pydantic, no http concerns); the
gRPC layer converts them to protobuf messages in ``app.grpc_app.converters``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class BookResponse:
    id: int
    title: str
    author: str
    isbn: str | None
    total_copies: int
    available_copies: int
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class MemberResponse:
    id: int
    full_name: str
    email: str
    phone: str | None
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class LoanResponse:
    id: int
    book_id: int
    member_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    is_overdue: bool


@dataclass(slots=True)
class TokenResponse:
    access_token: str
    expires_in: int
    token_type: str = "bearer"
