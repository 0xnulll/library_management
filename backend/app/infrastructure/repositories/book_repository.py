from __future__ import annotations

from sqlalchemy import or_, select, update

from app.domain.entities import Book
from app.domain.exceptions import ConflictError
from app.infrastructure.db.models import BookModel
from app.infrastructure.repositories.base_repository import BaseRepository


def _to_entity(row: BookModel) -> Book:
    return Book(
        id=row.id,
        title=row.title,
        author=row.author,
        isbn=row.isbn,
        total_copies=row.total_copies,
        active_loan_count=row.active_loan_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlBookRepository(BaseRepository):
    def add(self, book: Book) -> Book:
        row = BookModel(
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            total_copies=book.total_copies,
            active_loan_count=0,
        )
        self._session.add(row)
        self._session.flush()
        return _to_entity(row)

    def get(self, book_id: int) -> Book | None:
        row = self._session.get(BookModel, book_id)
        return _to_entity(row) if row else None

    def update(self, book: Book) -> Book:
        row = self._session.get(BookModel, book.id)
        if row is None:
            raise ValueError(f"book {book.id} not found")
        row.title = book.title
        row.author = book.author
        row.isbn = book.isbn
        row.total_copies = book.total_copies
        # active_loan_count is intentionally NOT mutated here — the source of
        # truth is borrow/return via increment/decrement_active_loans below.
        self._session.flush()
        return _to_entity(row)

    def search(self, query: str | None, limit: int, offset: int) -> list[Book]:
        stmt = select(BookModel).order_by(BookModel.title.asc())
        if query:
            like = f"%{query.lower()}%"
            stmt = stmt.where(
                or_(
                    BookModel.title.ilike(like),
                    BookModel.author.ilike(like),
                    BookModel.isbn.ilike(like),
                )
            )
        stmt = stmt.limit(limit).offset(offset)
        return [_to_entity(r) for r in self._session.execute(stmt).scalars().all()]

    def lock_for_update(self, book_id: int) -> Book | None:
        """Acquire an exclusive row lock on the book.

        On PostgreSQL this issues ``SELECT ... FOR UPDATE``. On engines that do
        not understand it (e.g. SQLite) we issue a no-op ``UPDATE`` against the
        row first; this still acquires a write lock at the row/database level
        and serializes concurrent borrowers.
        """
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        if dialect == "postgresql":
            stmt = select(BookModel).where(BookModel.id == book_id).with_for_update()
            row = self._session.execute(stmt).scalar_one_or_none()
            return _to_entity(row) if row else None

        bumped = self._session.execute(
            update(BookModel)
            .where(BookModel.id == book_id)
            .values(total_copies=BookModel.total_copies)
        )
        if bumped.rowcount == 0:
            return None
        # Force re-read so SQLAlchemy's identity map sees the latest column values
        # rather than a stale snapshot.
        row = self._session.get(BookModel, book_id)
        if row is None:
            return None
        self._session.refresh(row)
        return _to_entity(row)

    # ─── denormalized counter ───────────────────────────────────────────────
    #
    # The hot read paths (search/get/list) read ``active_loan_count`` directly
    # off the row instead of running ``COUNT(*)`` against ``loans``. The two
    # methods below are the only mutators of that field; they are atomic at the
    # SQL level and must run inside the same transaction as the corresponding
    # loan insert/update so the counter is never observably out-of-sync.

    def increment_active_loans(self, book_id: int) -> None:
        """Atomically add 1 to active_loan_count, refusing if it would exceed
        total_copies. Raises ConflictError if the invariant would be violated.
        """
        result = self._session.execute(
            update(BookModel)
            .where(
                BookModel.id == book_id,
                BookModel.active_loan_count < BookModel.total_copies,
            )
            .values(active_loan_count=BookModel.active_loan_count + 1)
        )
        if result.rowcount == 0:
            raise ConflictError("no copies available")

    def decrement_active_loans(self, book_id: int) -> None:
        """Atomically subtract 1; never goes below zero (protected by both the
        WHERE clause and the CHECK constraint).
        """
        self._session.execute(
            update(BookModel)
            .where(BookModel.id == book_id, BookModel.active_loan_count > 0)
            .values(active_loan_count=BookModel.active_loan_count - 1)
        )
