from __future__ import annotations

from pydantic import Field, field_validator

from app.grpc_app.dto._base import _DTO


class CreateBookDTO(_DTO):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    total_copies: int = Field(ge=0)

    @field_validator("isbn", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class UpdateBookDTO(_DTO):
    id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    total_copies: int = Field(ge=0)

    @field_validator("isbn", mode="before")
    @classmethod
    def _empty_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
