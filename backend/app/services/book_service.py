from __future__ import annotations

import logging

from app.domain.entities import Book
from app.domain.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.repositories import BookRepository
from app.services.response_type import BookResponse

logger = logging.getLogger(__name__)


class BookService:
    """CRUD/search operations for books.

    ``available_copies`` is computed from the denormalized ``active_loan_count``
    stored on each book row, so list/search are constant queries regardless of
    page size — no JOIN/COUNT against the loans table.
    """

    def __init__(self, books: BookRepository) -> None:
        self._books = books

    @staticmethod
    def _to_response(book: Book) -> BookResponse:
        return BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            total_copies=book.total_copies,
            available_copies=max(0, book.total_copies - book.active_loan_count),
            created_at=book.created_at,
            updated_at=book.updated_at,
        )

    def create(
        self, *, title: str, author: str, isbn: str | None, total_copies: int
    ) -> BookResponse:
        if isbn:
            for existing in self._books.search(isbn, limit=1, offset=0):
                if existing.isbn == isbn:
                    raise ConflictError(f"book with ISBN {isbn} already exists")
        book = Book(
            id=None,
            title=title,
            author=author,
            isbn=isbn,
            total_copies=total_copies,
            active_loan_count=0,
        )
        saved = self._books.add(book)
        logger.info("book.created", extra={"book_id": saved.id, "isbn": isbn})
        return self._to_response(saved)

    def update(
        self,
        book_id: int,
        *,
        title: str,
        author: str,
        isbn: str | None,
        total_copies: int,
    ) -> BookResponse:
        existing = self._books.get(book_id)
        if existing is None:
            raise NotFoundError(f"book {book_id} not found")
        if total_copies < existing.active_loan_count:
            raise ValidationError(
                f"cannot reduce total_copies below active loans "
                f"({existing.active_loan_count})"
            )
        existing.title = title
        existing.author = author
        existing.isbn = isbn
        existing.total_copies = total_copies
        saved = self._books.update(existing)
        logger.info("book.updated", extra={"book_id": book_id})
        return self._to_response(saved)

    def get(self, book_id: int) -> BookResponse:
        book = self._books.get(book_id)
        if book is None:
            raise NotFoundError(f"book {book_id} not found")
        return self._to_response(book)

    def search(self, query: str | None, limit: int, offset: int) -> list[BookResponse]:
        return [self._to_response(b) for b in self._books.search(query, limit, offset)]
