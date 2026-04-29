from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.domain.entities import Loan
from app.domain.exceptions import ConflictError, NotFoundError
from app.infrastructure.repositories import (
    SqlBookRepository,
    SqlLoanRepository,
    SqlMemberRepository,
)
from app.services.clock import Clock
from app.services.response_type import LoanResponse


class LoanService:
    """Application service for borrow/return operations.

    Concurrency: borrow() acquires a row-level lock on the book before counting
    active loans, so two simultaneous borrowers of the same single-copy book are
    serialized and the second one fails cleanly with ConflictError instead of
    over-allocating.
    """

    def __init__(
        self,
        books: SqlBookRepository,
        members: SqlMemberRepository,
        loans: SqlLoanRepository,
        clock: Clock,
        settings: Settings,
    ) -> None:
        self._books = books
        self._members = members
        self._loans = loans
        self._clock = clock
        self._settings = settings

    def _to_response(self, loan: Loan) -> LoanResponse:
        return LoanResponse(
            id=loan.id or 0,
            book_id=loan.book_id,
            member_id=loan.member_id,
            borrowed_at=loan.borrowed_at,
            due_at=loan.due_at,
            returned_at=loan.returned_at,
            is_overdue=loan.is_overdue(self._clock.now()),
        )

    def borrow(self, *, book_id: int, member_id: int, days: int | None = None) -> LoanResponse:
        if self._members.get(member_id) is None:
            raise NotFoundError(f"member {member_id} not found")

        book = self._books.lock_for_update(book_id)
        if book is None:
            raise NotFoundError(f"book {book_id} not found")

        active = self._loans.count_active_for_book(book_id)
        if active >= book.total_copies:
            raise ConflictError("no copies available")

        existing = self._loans.find_active_by_book_and_member(book_id, member_id)
        if existing is not None:
            raise ConflictError("member already has an active loan for this book")

        now = self._clock.now()
        loan_days = days or self._settings.default_loan_days
        loan = Loan(
            id=None,
            book_id=book_id,
            member_id=member_id,
            borrowed_at=now,
            due_at=now + timedelta(days=loan_days),
            returned_at=None,
        )
        return self._to_response(self._loans.add(loan))

    def return_book(self, loan_id: int) -> LoanResponse:
        loan = self._loans.get(loan_id)
        if loan is None:
            raise NotFoundError(f"loan {loan_id} not found")
        if not loan.is_active:
            raise ConflictError("loan already returned")
        loan.returned_at = self._clock.now()
        return self._to_response(self._loans.update(loan))

    def list_for_member(self, member_id: int) -> list[LoanResponse]:
        if self._members.get(member_id) is None:
            raise NotFoundError(f"member {member_id} not found")
        return [self._to_response(loan) for loan in self._loans.list_active_by_member(member_id)]

    def list(
        self,
        *,
        member_id: int | None,
        book_id: int | None,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> list[LoanResponse]:
        return [
            self._to_response(loan)
            for loan in self._loans.list(
                member_id=member_id,
                book_id=book_id,
                active_only=active_only,
                limit=limit,
                offset=offset,
            )
        ]
