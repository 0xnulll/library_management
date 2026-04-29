from __future__ import annotations

from pydantic import EmailStr, Field, field_validator

from app.grpc_app.dto._base import _DTO


class CreateMemberDTO(_DTO):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=64)

    @field_validator("phone", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class UpdateMemberDTO(_DTO):
    id: int = Field(gt=0)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=64)

    @field_validator("phone", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

