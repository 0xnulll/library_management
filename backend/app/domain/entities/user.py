from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class StaffUser:
    id: int
    username: str
    password_hash: str
    is_active: bool = True
    created_at: datetime | None = None
