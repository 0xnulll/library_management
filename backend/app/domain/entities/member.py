from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Member:
    id: int
    full_name: str
    email: str
    phone: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
