from __future__ import annotations

from sqlalchemy import or_, select, update

from app.domain.entities import Book
from app.infrastructure.db.models import BookModel
from app.infrastructure.repositories.base_repository import BaseRepository


def _to_entity(row: BookModel) -> Book:
    return Book(
        id=row.id,
        title=row.title,
        author=row.author,
        isbn=row.isbn,
        total_copies=row.total_copies,
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
        row = self._session.get(BookModel, book_id)
        return _to_entity(row) if row else None
