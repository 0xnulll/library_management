from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Book:
    id: int
    title: str
    author: str
    isbn: str | None
    total_copies: int
    active_loan_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
