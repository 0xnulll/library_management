from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(slots=True)
class Loan:
    id: int
    book_id: int
    member_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    def is_overdue(self, now: datetime) -> bool:
        return self.is_active and _as_aware(now) > _as_aware(self.due_at)
