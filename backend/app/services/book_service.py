from __future__ import annotations

from app.domain.entities import Book
from app.domain.exceptions import ConflictError, NotFoundError
from app.infrastructure.repositories import SqlBookRepository, SqlLoanRepository
from app.services.response_type import BookResponse


class BookService:
    def __init__(self, books: SqlBookRepository, loans: SqlLoanRepository) -> None:
        self._books = books
        self._loans = loans

    def _to_response(self, book: Book) -> BookResponse:
        active = self._loans.count_active_for_book(book.id)
        return BookResponse(
            id=book.id,
            title=book.title,
            author=book.author,
            isbn=book.isbn,
            total_copies=book.total_copies,
            available_copies=max(0, book.total_copies - active),
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
        )
        return self._to_response(self._books.add(book))

    def update(
        self,
        book_id: int,
        *,
        title: str,
        author: str,
        isbn: str | None,
        total_copies: int,
    ) -> BookResponse:
        from app.domain.exceptions import ValidationError

        existing = self._books.get(book_id)
        if existing is None:
            raise NotFoundError(f"book {book_id} not found")
        active = self._loans.count_active_for_book(book_id)
        if total_copies < active:
            raise ValidationError(
                f"cannot reduce total_copies below active loans ({active})"
            )
        existing.title = title
        existing.author = author
        existing.isbn = isbn
        existing.total_copies = total_copies
        return self._to_response(self._books.update(existing))

    def get(self, book_id: int) -> BookResponse:
        book = self._books.get(book_id)
        if book is None:
            raise NotFoundError(f"book {book_id} not found")
        return self._to_response(book)

    def search(self, query: str | None, limit: int, offset: int) -> list[BookResponse]:
        return [self._to_response(b) for b in self._books.search(query, limit, offset)]
