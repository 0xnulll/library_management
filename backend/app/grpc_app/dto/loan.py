from __future__ import annotations

from pydantic import Field, field_validator

from app.grpc_app.dto._base import _DTO


class BorrowDTO(_DTO):
    book_id: int = Field(gt=0)
    member_id: int = Field(gt=0)
    days: int | None = Field(default=None, ge=1, le=365)

    @field_validator("days", mode="before")
    @classmethod
    def _zero_to_none(cls, v: object) -> object:
        if v == 0:
            return None
        return v


class ReturnLoanDTO(_DTO):
    loan_id: int = Field(gt=0)