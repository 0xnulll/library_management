from __future__ import annotations

from sqlalchemy import func, select

from app.domain.entities import Loan
from app.infrastructure.db.models import LoanModel
from app.infrastructure.repositories.base_repository import BaseRepository


def _to_entity(row: LoanModel) -> Loan:
    return Loan(
        id=row.id,
        book_id=row.book_id,
        member_id=row.member_id,
        borrowed_at=row.borrowed_at,
        due_at=row.due_at,
        returned_at=row.returned_at,
    )


class SqlLoanRepository(BaseRepository):
    def add(self, loan: Loan) -> Loan:
        row = LoanModel(
            book_id=loan.book_id,
            member_id=loan.member_id,
            borrowed_at=loan.borrowed_at,
            due_at=loan.due_at,
            returned_at=loan.returned_at,
        )
        self._session.add(row)
        self._session.flush()
        return _to_entity(row)

    def get(self, loan_id: int) -> Loan | None:
        row = self._session.get(LoanModel, loan_id)
        return _to_entity(row) if row else None

    def update(self, loan: Loan) -> Loan:
        row = self._session.get(LoanModel, loan.id)
        if row is None:
            raise ValueError(f"loan {loan.id} not found")
        row.returned_at = loan.returned_at
        row.due_at = loan.due_at
        self._session.flush()
        return _to_entity(row)

    def count_active_for_book(self, book_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(LoanModel)
            .where(LoanModel.book_id == book_id, LoanModel.returned_at.is_(None))
        )
        return int(self._session.execute(stmt).scalar_one())

    def find_active_by_book_and_member(self, book_id: int, member_id: int) -> Loan | None:
        stmt = select(LoanModel).where(
            LoanModel.book_id == book_id,
            LoanModel.member_id == member_id,
            LoanModel.returned_at.is_(None),
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _to_entity(row) if row else None

    def list_active_by_member(self, member_id: int) -> list[Loan]:
        stmt = (
            select(LoanModel)
            .where(LoanModel.member_id == member_id, LoanModel.returned_at.is_(None))
            .order_by(LoanModel.borrowed_at.desc())
        )
        return [_to_entity(r) for r in self._session.execute(stmt).scalars().all()]

    def list(
        self,
        *,
        member_id: int | None,
        book_id: int | None,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> list[Loan]:
        stmt = select(LoanModel).order_by(LoanModel.borrowed_at.desc())
        if member_id is not None:
            stmt = stmt.where(LoanModel.member_id == member_id)
        if book_id is not None:
            stmt = stmt.where(LoanModel.book_id == book_id)
        if active_only:
            stmt = stmt.where(LoanModel.returned_at.is_(None))
        stmt = stmt.limit(limit).offset(offset)
        return [_to_entity(r) for r in self._session.execute(stmt).scalars().all()]
